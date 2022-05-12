#
#   MC68000 disassembler
#

import getopt
import os
import sys

buffer = bytearray(0x1000000)
jumplabel = [False] * 0x1000000
label = [False] * 0x1000000
location = 0
opcode = 0
flags = ''

def fetch():
    global buffer, location
    c = buffer[location]
    location += 1
    return c

def fetch16():
    global buffer, location
    c = buffer[location] << 8 | buffer[location + 1]
    location += 2
    return c

def displacement():
    disp = (lambda x : x & 0x7fff | -(x & 0x8000))(fetch16())
    return ('-' if disp < 0 else '') + f'${abs(disp):0=4x}'

def am_relative8():
    global jumplabel, buffer, location, flags
    ea = location + (lambda x : x & 0x7f | -(x & 0x80))(buffer[location - 1]) & 0xffffff
    jumplabel[ea] = True
    return f'L{ea:0=6x}'

def am_relative16():
    global jumplabel, label, location, flags
    ea = location + (lambda x : x & 0x7fff | -(x & 0x8000))(fetch16()) & 0xffffff
    if 'B' in flags:
        jumplabel[ea] = True
    else:
        label[ea] = True
    return f'L{ea:0=6x}'

def am_index(base):
    operand = fetch16()
    if operand & 0x700:
        return ''
    disp = operand & 0x7f | -(operand & 0x80)
    reg = ['d', 'a'][operand >> 15] + str(operand >> 12 & 7) + ['.w', '.l'][operand >> 11 & 1]
    return ('(-' if disp < 0 else '(') + f'${abs(disp):0=2x},{base},{reg})' if disp else f'({base},{reg})'

def am_absolute16():
    global jumplabel, label, flags
    operand = (lambda x : x & 0x7fff | -(x & 0x8000))(fetch16())
    ea = operand & 0xffffff
    if ea < start or ea > end:
        return ('(-' if operand < 0 else '(') + f'${abs(operand):0=4x})'
    if 'B' in flags:
        jumplabel[ea] = True
    else:
        label[ea] = True
    return f'(L{ea:0=6x}).w'

def am_absolute32():
    global jumplabel, label, flags
    operand = fetch16() << 16 | fetch16()
    ea = operand & 0xffffff
    if ea < start or ea > end:
        return f'(${operand:0=8x})' + ('.l' if ea < 0x8000 or ea >= 0xff8000 else '')
    if 'B' in flags:
        jumplabel[ea] = True
    else:
        label[ea] = True
    return f'(L{ea:0=6x})'

def am_immediate8():
    return f'#${fetch16() & 0xff:0=2x}'

def am_immediate16():
    global label, flags
    operand = fetch16()
    address = operand & 0x7fff | -(operand & 0x8000) & 0xff0000
    if 'P' in flags and address >= start and address <= end:
        label[address] = True
        return f'#L{address:0=6x}'
    return f'#${operand:0=4x}'

def am_immediate32():
    global label, flags
    operand = fetch16() << 16 | fetch16()
    address = operand & 0xffffff
    if 'P' in flags and address >= start and address <= end:
        label[address] = True
        return f'#L{address:0=6x}'
    return f'#${operand:0=8x}'

def am(size, ea, n):
    if ea >= 12 or n >= 8:
        return None, None, []
    str1 = (f'D{n}', f'A{n}', f'(A{n})', f'(A{n})+', f'-(A{n})', f'd(A{n})', f'd(A{n},Xi)', 'Abs.W', 'Abs.L', 'd(PC)', 'd(PC,Xi)', '#<data>')[ea]
    str2 = (f'D{n}', f'A{n}', f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}', '({},PC)', '{}', '{}')[ea]
    fnc_imm = {'B':am_immediate8, 'W':am_immediate16, 'L':am_immediate32}.get(size)
    fnc = {5:displacement, 6:lambda: am_index(f'a{n}'), 7:am_absolute16, 8:am_absolute32, 9:am_relative16, 10:lambda: am_index('pc'), 11:fnc_imm}.get(ea)
    return str1, str2, [fnc] if fnc else []

def branch16():
    global jumplabel, location, flags
    base = location
    disp = (lambda x : x & 0x7fff | -(x & 0x8000))(fetch16())
    ea = base + disp & 0xffffff
    jumplabel[ea] = True
    return ('.w' if disp >= -0x80 and disp < 0x80 else '') + f'\tL{ea:0=6x}'

def register_list():
    global buffer, location
    ea = buffer[location - 1] >> 3 & 7
    mask = f'{fetch16():0=16b}' if ea == 4 else f'{fetch16():0=16b}'[::-1]
    regs = []
    prev = '0'
    for r, slice in (('d', mask[:8]), ('a', mask[8:])):
        for i, c in enumerate(slice + '0'):
            if c == '1' and prev == '0':
                start = i
            if c == '0' and prev == '1':
                regs += [f'{r}{start}-{r}{i - 1}'] if i - start > 1 else [f'{r}{start}']
            prev = c
    return '/'.join(regs)

def movem():
    global buffer, location
    modreg = buffer[location - 1] & 0x3f; ea = modreg >> 3; n = modreg & 7; ea += n if ea == 7 else 0; str1, str2, fnc = am('', ea, n); regs = register_list()
    return f'{str2.lower().format(*[f() for f in fnc])},{regs}'

table = {
    0x003c: ('ORI #<data>,CCR',  '',   'ORI.B\t{},CCR',  am_immediate8),
    0x007c: ('ORI #<data>,SR',   '',   'ORI.W\t{},SR',   am_immediate16), 
    0x023c: ('ANDI #<data>,CCR', '',   'ANDI.B\t{},CCR', am_immediate8),
    0x027c: ('ANDI #<data>,SR',  '',   'ANDI.W\t{},SR',  am_immediate16),
    0x0a3c: ('EORI #<data>,CCR', '',   'EORI.B\t{},CCR', am_immediate8),
    0x0a7c: ('EORI t#<data>,SR', '',   'EORI.W\t{},SR',  am_immediate16),
    0x4afc: ('ILLEGAL',          '',   'ILLEGAL'),
    0x4e70: ('RESET',            '',   'RESET'),
    0x4e71: ('NOP',              '',   'NOP'),
    0x4e72: ('STOP #xxx',        '',   'STOP\t{}',       am_immediate16),
    0x4e73: ('RTE',              'A',  'RTE'),
    0x4e75: ('RTS',              'A',  'RTS'),
    0x4e76: ('TRAPV',            '',   'TRAPV'),
    0x4e77: ('RTR',              'A',  'RTR'),
    0x6000: ('BRA.W <label>',    'AB', 'BRA{}',          branch16),
    0x6100: ('BSR.W <label>',    'B',  'BSR{}',          branch16),
    0x6200: ('BHI.W <label>',    'B',  'BHI{}',          branch16),
    0x6300: ('BLS.W <label>',    'B',  'BLS{}',          branch16),
    0x6400: ('BCC.W <label>',    'B',  'BCC{}',          branch16),
    0x6500: ('BCS.W <label>',    'B',  'BCS{}',          branch16),
    0x6600: ('BNE.W <label>',    'B',  'BNE{}',          branch16),
    0x6700: ('BEQ.W <label>',    'B',  'BEQ{}',          branch16),
    0x6800: ('BVC.W <label>',    'B',  'BVC{}',          branch16),
    0x6900: ('BVS.W <label>',    'B',  'BVS{}',          branch16),
    0x6a00: ('BPL.W <label>',    'B',  'BPL{}',          branch16),
    0x6b00: ('BMI.W <label>',    'B',  'BMI{}',          branch16),
    0x6c00: ('BGE.W <label>',    'B',  'BGE{}',          branch16),
    0x6d00: ('BLT.W <label>',    'B',  'BLT{}',          branch16),
    0x6e00: ('BGT.W <label>',    'B',  'BGT{}',          branch16),
    0x6f00: ('BLE.W <label>',    'B',  'BLE{}',          branch16),
}

# table construction
# move
for i in range(0x1000):
    x = i >> 9 & 7; dst = i >> 6 & 7; src = i >> 3 & 7; y = i & 7; dst += x if dst == 7 else 0; src += y if src == 7 else 0
    if dst >= 9 or src >= 12:
        continue
    a, flg_a = ('A', 'P') if dst == 1 else ('', '')
    if dst != 1 and src != 1:
        str1_src, str2_src, fnc_src = am('B', src, y); str1_dst, str2_dst, fnc_dst = am('', dst, x)
        table[0x1000 | i] = (f'MOVE.B {str1_src},{str1_dst}', '', f'MOVE.B\t{str2_src},{str2_dst}', *fnc_src + fnc_dst)
    str1_src, str2_src, fnc_src = am('W', src, y); str1_dst, str2_dst, fnc_dst = am('', dst, x)
    table[0x3000 | i] = (f'MOVE{a}.W {str1_src},{str1_dst}', f'{flg_a}', f'MOVE{a}.W\t{str2_src},{str2_dst}', *fnc_src + fnc_dst)
    str1_src, str2_src, fnc_src = am('L', src, y); str1_dst, str2_dst, fnc_dst = am('', dst, x)
    table[0x2000 | i] = (f'MOVE{a}.L {str1_src},{str1_dst}', f'{flg_a}', f'MOVE{a}.L\t{str2_src},{str2_dst}', *fnc_src + fnc_dst)

# standard
for i in range(0x1000):
    x = i >> 9 & 7; op = i >> 6 & 7; ea = i >> 3 & 7; y = i & 7; ea += y if ea == 7 else 0
    if ea >= (12, 12, 12, 12, 9, 9, 9, 12)[op]:
        continue
    a = 'A' if op == 3 or op == 7 else ''; size = 'BWLWBWLL'[op]; str1, str2, fnc = am(size, ea, y)
    str1, str2 = map(lambda y : {'S':f'{y},D{x}', 'D':f'D{x},{y}', 'A':f'{y},A{x}'}['SSSADDDA'[op]], (str1, str2))
    if op != 3 and op != 7 and ea != 1 and not (op >= 4 and op < 7 and ea == 0):
        table[0x8000 | i] = (f'OR.{size} {str1}', '', f'OR.{size}\t{str2}', *fnc)
        table[0xc000 | i] = (f'AND.{size} {str1}', '', f'AND.{size}\t{str2}', *fnc)
    if not (op == 0 and ea == 1) and not (op >= 4 and op < 7 and ea < 2):
        table[0x9000 | i] = (f'SUB{a}.{size} {str1}', '', f'SUB{a}.{size}\t{str2}', *fnc)
        table[0xd000 | i] = (f'ADD{a}.{size} {str1}', '', f'ADD{a}.{size}\t{str2}', *fnc)
    if not (op == 0 and ea == 1) and not (op >= 4 and op < 7):
        table[0xb000 | i] = (f'CMP{a}.{size} {str1}', '', f'CMP{a}.{size}\t{str2}', *fnc)
    if op >= 4 and op < 7 and ea != 1:
        table[0xb000 | i] = (f'EOR.{size} {str1}', '', f'EOR.{size}\t{str2}', *fnc)
    if (op == 3 or op == 7) and ea != 1:
        s = 'S' if op == 7 else 'U'; str1, str2, fnc = am('W', ea, y)
        table[0x8000 | i] = (f'DIV{s}.W {str1},D{x}', '', f'DIV{s}.W\t{str2},D{x}', *fnc)
        table[0xc000 | i] = (f'MUL{s}.W {str1},D{x}', '', f'MUL{s}.W\t{str2},D{x}', *fnc)

# immediate
for i in range(0xc0):
    ea = i >> 3 & 7; n = i & 7; ea += n if ea == 7 else 0
    if ea == 1 or ea >= 9:
        continue
    size = 'BWL'[i >> 6]; str1, str2, fnc = am('', ea, n); fnc = [{'B':am_immediate8, 'W':am_immediate16, 'L':am_immediate32}[size]] + fnc
    for base, op in {0x0000:'ORI', 0x0200:'ANDI', 0x0400:'SUBI', 0x0600:'ADDI', 0x0a00:'EORI', 0x0c00:'CMPI'}.items():
        table[base | i] = (f'{op}.{size} #<data>,{str1}', '', f'{op}.{size}\t''{},'f'{str2}', *fnc)
for i in range(0x1000):
    data = i >> 9 & 7; size = i >> 6 & 3; ea = i >> 3 & 7; n = i & 7; ea += n if ea == 7 else 0
    if size == 3 or ea >= 9 or size == 0 and ea == 1:
        continue
    op = ('ADDQ', 'SUBQ')[i >> 8 & 1]; size = 'BWL'[size]; str1, str2, fnc = am('', ea, n)
    table[0x5000 | i] = (f'{op}.{size} #{data if data else 8},{str1}', '', f'{op}.{size}\t#{data if data else 8},{str2}', *fnc)
for i in range(0x1000):
    if i & 0x100:
        continue
    data = (lambda x : x & 0x7f | -(x & 0x80))(i); str_data = f'#${data:0=2x}' if data >= 0 else f'#-${-data:0=2x}'
    table[0x7000 | i] = (f'MOVEQ.L {str_data},D{i >> 9}', '', f'MOVEQ.L\t{str_data},D{i >> 9}')

# single operand
for i in range(0xc0):
    ea = i >> 3 & 7; n = i & 7; ea += n if ea == 7 else 0
    if ea == 1 or ea >= 9:
        continue
    size = 'BWL'[i >> 6]; str1, str2, fnc = am('', ea, n)
    for base, op in {0x4000:'NEGX', 0x4200:'CLR', 0x4400:'NEG', 0x4600:'NOT', 0x4a00:'TST'}.items():
        table[base | i] = (f'{op}.{size} {str1}', '', f'{op}.{size}\t{str2}', *fnc)
    if size == 'B':
        table[0x4800 | i] = (f'NBCD.B {str1}', '', f'NBCD.B\t{str2}', *fnc)
for i in range(0xc0, 0x100):
    ea = i >> 3 & 7; n = i & 7; ea += n if ea == 7 else 0
    if ea == 1 or ea >= 9:
        continue
    str1, str2, fnc = am('', ea, n)
    for base, op in {0x4a00:'TAS', 0x5000:'ST', 0x5100:'SF', 0x5200:'SHI', 0x5300:'SLS', 0x5400:'SCC', 0x5500:'SCS', 0x5600:'SNE', 0x5700:'SEQ',
                     0x5800:'SVC', 0x5900:'SVS', 0x5a00:'SPL', 0x5b00:'SMI', 0x5c00:'SGE', 0x5d00:'SLT', 0x5e00:'SGT', 0x5f00:f'SLE'}.items():
        table[base | i] = (f'{op}.B {str1}', '', f'{op}.B\t{str2}', *fnc)

# shift/rotate
for i in range(0x1000):
    y = i >> 9; dr = 'RL'[i >> 8 & 1]; size = i >> 6 & 3; n = i & 7
    if size < 3:
        size = 'BWL'[size]; str_src = (f'#{y if y else 8}', f'D{y}')[i >> 5 & 1]; op = ('AS', 'LS', 'ROX', 'RO')[i >> 3 & 3]
        table[0xe000 | i] = (f'{op}{dr}.{size} {str_src},D{n}', '', f'{op}{dr}.{size}\t{str_src},D{n}')
    else:
        ea = i >> 3 & 7; ea += n if ea == 7 else 0
        if y >= 4 or ea < 2 or ea >= 9:
            continue
        op = ('AS', 'LS', 'ROX', 'RO')[y]; str1, str2, fnc = am('', ea, n)
        table[0xe000 | i] = (f'{op}{dr}.W {str1}', '', f'{op}{dr}.W\t{str2}', *fnc)

# bit manipulation
for i in range(0x1000):
    y = i >> 9; dyn = i >> 8 & 1; ea = i >> 3 & 7; n = i & 7; ea += n if ea == 7 else 0
    if not dyn and y != 4 or ea == 1 or ea >= 9:
        continue
    str1_src = ('#<data>', f'D{y}')[dyn]; str2_src = ('{}', f'D{y}')[dyn]
    size = 'L' if ea == 0 else 'B'; str1, str2, fnc = am('', ea, n); op = ('BTST', 'BCHG', 'BCLR', 'BSET')[i >> 6 & 3]
    table[0x0000 | i] = (f'{op}.{size} {str1_src},{str1}', '', f'{op}.{size}\t{str2_src},{str2}', *([] if dyn else [am_immediate8]) + fnc)

# branch
for i in range(0x100):
    n = i & 7
    if i:
        table[0x6000 | i] = ('BRA.B <label>', 'AB', 'BRA\t{}', am_relative8)
        for base, op in {0x6100:'BSR', 0x6200:'BHI', 0x6300:'BLS', 0x6400:'BCC', 0x6500:'BCS', 0x6600:'BNE', 0x6700:'BEQ', 0x6800:'BVC',
                         0x6900:'BVS', 0x6a00:'BPL', 0x6b00:'BMI', 0x6c00:'BGE', 0x6d00:'BLT', 0x6e00:'BGT', 0x6f00:'BLE'}.items():
            table[base | i] = (f'{op}.B <label>', 'B', f'{op}\t''{}', am_relative8)
    if (i >> 3 & 0x1f) == 0x19:
        for base, op in {0x5000:'DBT', 0x5100:'DBRA', 0x5200:'DBHI', 0x5300:'DBLS', 0x5400:'DBCC', 0x5500:'DBCS', 0x5600:'DBNE', 0x5700:'DBEQ', 
                         0x5800:'DBVC', 0x5900:'DBVS', 0x5a00:'DBPL', 0x5b00:'DBMI', 0x5c00:'DBGE', 0x5d00:'DBLT', 0x5e00:'DBGT', 0x5f00:'DBLE'}.items():
            table[base | i] = (f'{op} D{n},<label>', 'B', f'{op}\tD{n},''{}', am_relative16)

# JMP, JSR, LEA, PEA, MOVEM
for i in range(0x40):
    ea = i >> 3; n = i & 7; ea += n if ea == 7 else 0
    if ea < 2 or ea >= 11:
        continue
    str1, str2, fnc = am('', ea, n)
    if ea != 3 and ea != 4:
        for y in range(8):
            table[0x41c0 | y << 9 | i] = (f'LEA.L {str1},A{y}', '', f'LEA.L\t{str2},A{y}', *fnc)
        table[0x4840 | i] = (f'PEA.L {str1}', '',   f'PEA.L\t{str2}', *fnc)
        table[0x4e80 | i] = (f'JSR {str1}', 'B', f'JSR\t{str2}', *fnc)
        table[0x4ec0 | i] = (f'JMP {str1}', 'AB', f'JMP\t{str2}', *fnc)
    if ea != 3 and ea < 9:
        table[0x4880 | i] = (f'MOVEM.W <register list>,{str1}', '', 'MOVEM.W\t{},'f'{str2}', register_list, *fnc)
        table[0x48c0 | i] = (f'MOVEM.L <register list>,{str1}', '', 'MOVEM.L\t{},'f'{str2}', register_list, *fnc)
    if ea != 4:
        table[0x4c80 | i] = (f'MOVEM.W {str1},<register list>', '', 'MOVEM.W\t{}', movem)
        table[0x4cc0 | i] = (f'MOVEM.L {str1},<register list>', '', 'MOVEM.L\t{}', movem)

# ADDX, CMPM. SUBX, ABCD, SBCD
for i in range(0x1000):
    x = i >> 9; size = i >> 6 & 3; rm = i >> 3 & 1; y = i & 7
    if (i & 0x130) != 0x100 or size == 3:
        continue
    size = 'BWL'[size]; str_rm = (f'D{y},D{x}', f'-(A{y}),-(A{x})')[rm];
    if size == 'B':
        table[0x8000 | i] = (f'SBCD.B {str_rm}', '', f'SBCD.B\t{str_rm}')
        table[0xc000 | i] = (f'ABCD.B {str_rm}', '', f'ABCD.B\t{str_rm}')
    if rm:
        table[0xb000 | i] = (f'CMPM.{size} (A{y})+,(A{x})+', '', f'CMPM.{size}\t(A{y})+,(A{x})+')
    table[0x9000 | i] = (f'SUBX.{size} {str_rm}', '', f'SUBX.{size}\t{str_rm}')
    table[0xd000 | i] = (f'ADDX.{size} {str_rm}', '', f'ADDX.{size}\t{str_rm}')

# miscellaneous
for i in range(0x1000):
    x = i >> 9; ea = i >> 3 & 7; y = i & 7; ea += y if ea == 7 else 0
    if (i >> 3 & 0x3f) == 0x21:
        table[0x0000 | i] = (f'MOVEP.W d(A{y}),D{x}', '', 'MOVEP.W\t({},'f'A{y}),D{x}', displacement)
    if (i >> 3 & 0x3f) == 0x29:
        table[0x0000 | i] = (f'MOVEP.L d(A{y}),D{x}', '', 'MOVEP.L\t({},'f'A{y}),D{x}', displacement)
    if (i >> 3 & 0x3f) == 0x31:
        table[0x0000 | i] = (f'MOVEP.W D{x},d(A{y})', '', f'MOVEP.W\tD{x},(''{},'f'A{y})', displacement)
    if (i >> 3 & 0x3f) == 0x39:
        table[0x0000 | i] = (f'MOVEP.L D{x},d(A{y})', '', f'MOVEP.L\tD{x},(''{},'f'A{y})', displacement)
    if (i >> 6 & 7) == 6 and ea != 1 and ea < 12:
        str1, str2, fnc = am('W', ea, y)
        table[0x4000 | i] = (f'CHK.W {str1},D{x}', '', f'CHK.W\t{str2},D{x}', *fnc)
    if (i >> 3 & 0x3f) == 0x28:
        table[0xc000 | i] = (f'EXG.L D{x},D{y}', '', f'EXG.L\tD{x},D{y}')
    if (i >> 3 & 0x3f) == 0x29:
        table[0xc000 | i] = (f'EXG.L A{x},A{y}', '', f'EXG.L\tA{x},A{y}')
    if (i >> 3 & 0x3f) == 0x31:
        table[0xc000 | i] = (f'EXG.L D{x},A{y}', '', f'EXG.L\tD{x},A{y}')
for i in range(0x40):
    ea = i >> 3; n = i & 7; ea += n if ea == 7 else 0
    if ea == 1 or ea >= 12:
        continue
    str1, str2, fnc = am('W', ea, n)
    if ea != 1 and ea < 9:
        table[0x40c0 | i] = (f'MOVE.W SR,{str1}', '', f'MOVE.W\tSR,{str2}', *fnc)
    if ea != 1:
        table[0x46c0 | i] = (f'MOVE.W {str1},SR', '', f'MOVE.W\t{str2},SR', *fnc)
    str1, str2, fnc = am('B', ea, n)
    if ea != 1:
        table[0x44c0 | i] = (f'MOVE.B {str1},CCR', '', f'MOVE.B\t{str2},CCR', *fnc)
for n in range(8):
    table[0x4840 | n] = (f'SWAP.W D{n}', '', f'SWAP.W\tD{n}')
    table[0x4880 | n] = (f'EXT.W D{n}', '', f'EXT.W\tD{n}')
    table[0x48c0 | n] = (f'EXT.L D{n}', '', f'EXT.L\tD{n}')
    table[0x4e50 | n] = (f'LINK A{n},#<displacement>', '', f'LINK.W\tA{n},' +'#{}', displacement)
    table[0x4e58 | n] = (f'UNLK A{n}', '', f'UNLK\tA{n}')
    table[0x4e60 | n] = (f'MOVE.L A{n},USP', '', f'MOVE.L\tA{n},USP')
    table[0x4e68 | n] = (f'MOVE.L USP,A{n}', '', f'MOVE.L\tUSP,A{n}')

def op():
    global flags, table
    opcode = fetch16()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[1]
    operands = [f() for f in t[3:]]
    return t[2].lower().format(*operands) if '' not in operands else ''

# main
opts, args = getopt.getopt(sys.argv[1:], "e:flo:s:t:")
if len(args) == 0:
    print(f'使い方: {os.path.basename(sys.argv[0])} [オプション] ファイル名')
    print(f'オプション:')
    print(f'  -e <アドレス>   エントリ番地を指定する')
    print(f'  -f              強制的に逆アセンブルする')
    print(f'  -l              アドレスとデータを出力する')
    print(f'  -o <ファイル名> 出力ファイルを指定する(デフォルト:標準出力)')
    print(f'  -s <アドレス>   開始番地を指定する(デフォルト:0)')
    print(f'  -t <ファイル名> ラベルテーブルを使用する')
    sys.exit(0)
remark = {}
code = [False] * 0x1000000
string = [False] * 0x1000000
bytestring = [False] * 0x1000000
pointer = [False] * 0x1000000
start = 0
end = 0
listing = False
entry = 0
noentry = True
file = sys.stdout
tablefile = None
for o, a in opts:
    if o == '-e':
        entry = int(a, 0)
        jumplabel[entry] = True
        noentry = False
    elif o == '-f':
        code = [True] * 0x1000000
    elif o == '-l':
        listing = True
    elif o == '-o':
        file = open(a, 'w', encoding='utf-8')
    elif o == '-s':
        start = int(a, 0)
        end = start
    elif o == '-t':
        tablefile = open(a, 'r', encoding='utf-8')
with open(args[0], 'rb') as f:
    data = f.read()
    end = min(start + len(data), 0x1000000)
    buffer[start:end] = data
if tablefile:
    for line in tablefile:
        words = line.split(' ')
        if words[0] == 'b':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            bytestring[base:base + size] = [True] * size
        elif words[0] == 'c':
            jumplabel[int(words[1], 16)] = True
            noentry = False
        elif words[0] == 'd':
            label[int(words[1], 16)] = True
        elif words[0] == 'r':
            addr = int(words[1], 16)
            if addr not in remark:
                remark[addr] = []
            remark[addr] += [line[len(words[0] + words[1]) + 2:].rstrip()]
        elif words[0] == 's':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            string[base:base + size] = [True] * size
        elif words[0] == 't':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 4, 4):
                pointer[i:i + 4] = [True] * 4
                jumplabel[int.from_bytes(buffer[i + 1:i + 4], 'big')] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 4, 4):
                pointer[i:i + 4] = [True] * 4
                label[int.from_bytes(buffer[i + 1:i + 4], 'big')] = True

# path 1
if noentry and start:
    entry = start
    jumplabel[entry] = True
elif noentry:
    label[start] = True
    reset = int.from_bytes(buffer[5:8], 'big')
    entry = reset if reset >= max(start, 8) and reset < end and not reset & 1 else start
    jumplabel[entry] = True
    for i in range(8, min(reset, 0x400), 4):
        vector = int.from_bytes(buffer[i + 1:i + 4], 'big')
        if vector >= max(start, 8) and vector < end and not vector & 1:
            jumplabel[vector] = True
while True:
    location = end
    for i in range(start, end):
        if jumplabel[i] and not code[i]:
            location = i
            break
    if location == end:
        break
    while True:
        base = location
        op()
        code[base:location] = [True] * (location - base)
        if 'A' in flags or location >= end or string[location] or bytestring[location] or pointer[location]:
            break

# path 2
if listing:
    print(f'\t\t\t\t;-----------------------------------------------', file=file)
    print(f'\t\t\t\t;\tMC68000 disassembler', file=file)
    print(f'\t\t\t\t;\tfilename: {args[0]}', file=file)
    print(f'\t\t\t\t;-----------------------------------------------', file=file)
    print(f'\t\t\t\t', file=file)
    print(f'\t\t\t\t\t.cpu\t68000', file=file)
    print(f'\t\t\t\t', file=file)
    print(f'\t\t\t\t\t.text', file=file)
    print(f'\t\t\t\t', file=file)
else:
    print(f';-----------------------------------------------', file=file)
    print(f';\tMC68000 disassembler', file=file)
    print(f';\tfilename: {args[0]}', file=file)
    print(f';-----------------------------------------------', file=file)
    print(f'', file=file)
    print(f'\t.cpu\t68000', file=file)
    print(f'', file=file)
    print(f'\t.text', file=file)
    print(f'', file=file)
location = start
while location < end:
    base = location
    if base in remark:
        for s in remark[base]:
            if listing:
                print(f'{base:0=6X}\t\t\t', end='', file=file)
            print(f';{s}', file=file)
    if code[base]:
        s = op()
        size = location - base
    else:
        s = ''
        size = 0
    if s != '':
        if jumplabel[base]:
            if listing:
                print(f'{base:0=6X}\t\t\t\t', end='', file=file)
            print(f'L{base:0=6x}:', file=file)
        if listing:
            print(f'{base:0=6X} ', end='', file=file)
            location = base
            for i in range(size):
                print(f' {fetch():0=2X}', end='', file=file)
            print('\t\t\t' if size < 4 else '\t\t' if size < 6 else '\t', end='', file=file)
        print('\t' + s, file=file)
    elif string[base]:
        if label[base]:
            if listing:
                print(f'{base:0=6X}\t\t\t\t', end='', file=file)
            print(f'L{base:0=6x}:', file=file)
        if listing:
            print(f'{base:0=6X}\t\t\t\t', end='', file=file)
        location = base
        print(f'\tfcc\t\'{fetch():c}', end='', file=file)
        while location < end and string[location] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif bytestring[base]:
        if label[base]:
            if listing:
                print(f'{base:0=6X}\t\t\t\t', end='', file=file)
            print(f'L{base:0=6x}:', file=file)
        if listing:
            print(f'{base:0=6X}\t\t\t\t', end='', file=file)
        location = base
        print(f'\t.dc.b\t${fetch():0=2x}', end='', file=file)
        for i in range(7):
            if location >= end or not bytestring[location] or label[location]:
                break
            print(f',${fetch():0=2x}', end='', file=file)
        print('', file=file)
    elif pointer[base]:
        if label[base]:
            if listing:
                print(f'{base:0=6X}\t\t\t\t', end='', file=file)
            print(f'L{base:0=6x}:', file=file)
        if listing:
            print(f'{base:0=6X}\t\t\t\t', end='', file=file)
        location = base
        print(f'\t.dc.l\tL{fetch16() << 16 | fetch16():0=6x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch16() << 16 | fetch16():0=6x}', end='', file=file)
        print('', file=file)
    elif code[base]:
        if jumplabel[base]:
            if listing:
                print(f'{base:0=6X}\t\t\t\t', end='', file=file)
            print(f'L{base:0=6x}:', file=file)
        if listing:
            print(f'{base:0=6X}\t\t\t\t', end='', file=file)
        location = base
        print(f'\t.dc.b\t${fetch():0=2x}', end='', file=file)
        for i in range(size - 1):
            print(f',${fetch():0=2x}', end='', file=file)
        print('', file=file)
    else:
        if label[base] or jumplabel[base]:
            if listing:
                print(f'{base:0=6X}\t\t\t\t', end='', file=file)
            print(f'L{base:0=6x}:', file=file)
        if listing:
            print(f'{base:0=6X}\t\t\t\t', end='', file=file)
        location = base
        print(f'\t.dc.b\t${fetch():0=2x}', end='', file=file)
        for i in range(7):
            if location >= end or code[location] or string[location] or bytestring[location] or pointer[location] or label[location] or jumplabel[base]:
                break
            print(f',${fetch():0=2x}', end='', file=file)
        print('', file=file)
if label[location] or jumplabel[location]:
    if listing:
        print(f'{location:0=6X}\t\t\t\t', end='', file=file)
    print(f'L{location:0=6x}:', file=file)
if listing:
    print(f'{location & 0xffffff:0=6X}\t\t\t\t', end='', file=file)
print(f'\t.end\tL{entry:0=6x}', file=file)

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

def am_index_a0():
    return am_index('a0')

def am_index_a1():
    return am_index('a1')

def am_index_a2():
    return am_index('a2')

def am_index_a3():
    return am_index('a3')

def am_index_a4():
    return am_index('a4')

def am_index_a5():
    return am_index('a5')

def am_index_a6():
    return am_index('a6')

def am_index_a7():
    return am_index('a7')

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

def am_index_pc():
    return am_index('pc')

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
    for i, c in enumerate(mask[:8] + '0'):
        if c == '1' and prev == '0':
            start = i
        if c == '0' and prev == '1':
            regs += [f'd{start}-d{i - 1}'] if i - start > 1 else [f'd{start}']
        prev = c
    for i, c in enumerate(mask[8:] + '0'):
        if c == '1' and prev == '0':
            start = i
        if c == '0' and prev == '1':
            regs += [f'a{start}-a{i - 1}'] if i - start > 1 else [f'a{start}']
        prev = c
    return '/'.join(regs)

fnc_index = [am_index_a0, am_index_a1, am_index_a2, am_index_a3, am_index_a4, am_index_a5, am_index_a6, am_index_a7]
fnc_ea = [None, None, None, None, None, displacement, None, am_absolute16, am_absolute32, am_relative16, am_index_pc, None]
fnc_imm = [am_immediate8, am_immediate16, am_immediate32, am_immediate16, am_immediate8, am_immediate16, am_immediate32, am_immediate32]

def movem():
    global buffer, location
    modreg = buffer[location - 1] & 0x3f
    ea = modreg >> 3; n = modreg & 7
    ea += n if ea == 7 else 0
    str_ea = [None, None, f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}', '({},PC)', '{}'][ea]
    regs = register_list()
    return f'{str_ea.lower().format(*([fnc_index[n]()] if ea == 6 else [fnc_ea[ea]()] if ea >= 5 else []))},{regs}'

table = {
0x003c: # ORI #<data>,CCR
    ('',   'ORI.B\t{},CCR',  am_immediate8),
0x007c: # ORI #<data>,SR
    ('',   'ORI.W\t{},SR',   am_immediate16), 
0x023c: # ANDI #<data>,CCR
    ('',   'ANDI.B\t{},CCR', am_immediate8),
0x027c: # ANDI #<data>,SR
    ('',   'ANDI.W\t{},SR',  am_immediate16),
0x0a3c: # EORI #<data>,CCR
    ('',   'EORI.B\t{},CCR', am_immediate8),
0x0a7c: # EORI t#<data>,SR
    ('',   'EORI.W\t{},SR',  am_immediate16),
0x4afc: # ILLEGAL
    ('',   'ILLEGAL'),
0x4e70: # RESET
    ('',   'RESET'),
0x4e71: # NOP
    ('',   'NOP'),
0x4e72: # STOP #xxx
    ('',   'STOP\t{}',       am_immediate16),
0x4e73: # RTE
    ('A',  'RTE'),
0x4e75: # RTS
    ('A',  'RTS'),
0x4e76: # TRAPV
    ('',   'TRAPV'),
0x4e77: # RTR
    ('A',  'RTR'),
0x6000: # BRA.W <label>
    ('AB', 'BRA{}',          branch16),
0x6100: # BSR.W <label>
    ('B',  'BSR{}',          branch16),
0x6200: # BHI.W <label>
    ('B',  'BHI{}',          branch16),
0x6300: # BLS.W <label>
    ('B',  'BLS{}',          branch16),
0x6400: # BCC.W <label>
    ('B',  'BCC{}',          branch16),
0x6500: # BCS.W <label>
    ('B',  'BCS{}',          branch16),
0x6600: # BNE.W <label>
    ('B',  'BNE{}',          branch16),
0x6700: # BEQ.W <label>
    ('B',  'BEQ{}',          branch16),
0x6800: # BVC.W <label>
    ('B',  'BVC{}',          branch16),
0x6900: # BVS.W <label>
    ('B',  'BVS{}',          branch16),
0x6a00: # BPL.W <label>
    ('B',  'BPL{}',          branch16),
0x6b00: # BMI.W <label>
    ('B',  'BMI{}',          branch16),
0x6c00: # BGE.W <label>
    ('B',  'BGE{}',          branch16),
0x6d00: # BLT.W <label>
    ('B',  'BLT{}',          branch16),
0x6e00: # BGT.W <label>
    ('B',  'BGT{}',          branch16),
0x6f00: # BLE.W <label>
    ('B',  'BLE{}',          branch16),
}

# table construction
# move
for i in range(0x1000):
    x = i >> 9 & 7; dst = i >> 6 & 7; src = i >> 3 & 7; y = i & 7
    dst += x if dst == 7 else 0; src += y if src == 7 else 0
    if dst >= 9 or src >= 12:
        continue
    flg_a = 'P' if dst == 1 else ''
    str_a = 'A' if dst == 1 else ''
    str_src = [f'D{y}', f'A{y}', f'(A{y})', f'(A{y})+', f'-(A{y})', '({},'f'A{y})', '{}', '{}', '{}', '({},PC)', '{}', '{}'][src]
    str_dst = [f'D{x}', f'A{x}', f'(A{x})', f'(A{x})+', f'-(A{x})', '({},'f'A{x})', '{}', '{}', '{}'][dst]
    if dst != 1 and src != 1:
        fncs = ([fnc_index[y]] if src == 6 else [am_immediate8] if src == 11 else [fnc_ea[src]] if src >= 5 else []) + ([fnc_index[x]] if dst == 6 else [fnc_ea[dst]] if dst >= 5 else [])
        table[0x1000 | i] = ('', f'MOVE.B\t{str_src},{str_dst}', *fncs)
    fncs = ([fnc_index[y]] if src == 6 else [am_immediate16] if src == 11 else [fnc_ea[src]] if src >= 5 else []) + ([fnc_index[x]] if dst == 6 else [fnc_ea[dst]] if dst >= 5 else [])
    table[0x3000 | i] = (f'{flg_a}', f'MOVE{str_a}.W\t{str_src},{str_dst}', *fncs)
    fncs = ([fnc_index[y]] if src == 6 else [am_immediate32] if src == 11 else [fnc_ea[src]] if src >= 5 else []) + ([fnc_index[x]] if dst == 6 else [fnc_ea[dst]] if dst >= 5 else [])
    table[0x2000 | i] = (f'{flg_a}', f'MOVE{str_a}.L\t{str_src},{str_dst}', *fncs)

# standard
for i in range(0x1000):
    x = i >> 9 & 7; op = i >> 6 & 7; ea = i >> 3 & 7; y = i & 7
    ea += y if ea == 7 else 0
    if ea >= [12, 12, 12, 12, 9, 9, 9, 12][op]:
        continue
    str_ea = [f'D{y}', f'A{y}', f'(A{y})', f'(A{y})+', f'-(A{y})', '({},'f'A{y})', '{}', '{}', '{}', '({},PC)', '{}', '{}'][ea]
    str_op = [f'.B\t{str_ea},D{x}', f'.W\t{str_ea},D{x}', f'.L\t{str_ea},D{x}', f'A.W\t{str_ea},A{x}', f'.B\tD{x},{str_ea}', f'.W\tD{x},{str_ea}', f'.L\tD{x},{str_ea}', f'A.L\t{str_ea},A{x}'][op]
    str_op2 = [None, None, None, f'U.W\t{str_ea},D{x}', None, None, None, f'S.W\t{str_ea},D{x}'][op]
    if op != 3 and op != 7 and ea != 1 and not (op >= 4 and op < 7 and ea == 0):
        table[0x8000 | i] = ('', f'OR{str_op}', *([fnc_index[y]] if ea == 6 else [fnc_imm[op]] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if (op == 3 or op == 7) and ea != 1:
        table[0x8000 | i] = ('', f'DIV{str_op2}', *([fnc_index[y]] if ea == 6 else [am_immediate16] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if not (op == 0 and ea == 1) and not (op >= 4 and op < 7 and ea < 2):
        table[0x9000 | i] = ('', f'SUB{str_op}', *([fnc_index[y]] if ea == 6 else [fnc_imm[op]] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if not (op == 0 and ea == 1) and not (op >= 4 and op < 7):
        table[0xb000 | i] = ('', f'CMP{str_op}', *([fnc_index[y]] if ea == 6 else [fnc_imm[op]] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if op >= 4 and op < 7 and ea != 1:
        table[0xb000 | i] = ('', f'EOR{str_op}', *([fnc_index[y]] if ea == 6 else [fnc_imm[op]] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if op != 3 and op != 7 and ea != 1 and not (op >= 4 and op < 7 and ea == 0):
        table[0xc000 | i] = ('', f'AND{str_op}', *([fnc_index[y]] if ea == 6 else [fnc_imm[op]] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if (op == 3 or op == 7) and ea != 1:
        table[0xc000 | i] = ('', f'MUL{str_op2}', *([fnc_index[y]] if ea == 6 else [am_immediate16] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if not (op == 0 and ea == 1) and not (op >= 4 and op < 7 and ea < 2):
        table[0xd000 | i] = ('', f'ADD{str_op}', *([fnc_index[y]] if ea == 6 else [fnc_imm[op]] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))

# immediate
for i in range(0x100):
    size = i >> 6; ea = i >> 3 & 7; n = i & 7
    ea += n if ea == 7 else 0
    if size == 3 or ea == 1 or ea >= 9:
        continue
    str_ea = [f'D{n}', None, f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}'][ea]
    str_op = ['.B\t{},' + f'{str_ea}', '.W\t{},' + f'{str_ea}', '.L\t{},' + f'{str_ea}'][size]
    table[0x0000 | i] = ('', f'ORI{str_op}', *([fnc_imm[size]] + ([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else [])))
    table[0x0200 | i] = ('', f'ANDI{str_op}', *([fnc_imm[size]] + ([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else [])))
    table[0x0400 | i] = ('', f'SUBI{str_op}', *([fnc_imm[size]] + ([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else [])))
    table[0x0600 | i] = ('', f'ADDI{str_op}', *([fnc_imm[size]] + ([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else [])))
    table[0x0a00 | i] = ('', f'EORI{str_op}', *([fnc_imm[size]] + ([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else [])))
    table[0x0c00 | i] = ('', f'CMPI{str_op}', *([fnc_imm[size]] + ([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else [])))
for i in range(0x1000):
    data = i >> 9 & 7; size = i >> 6 & 3; ea = i >> 3 & 7; n = i & 7
    ea += n if ea == 7 else 0
    if size == 3 or ea >= 9:
        continue
    data = 8 if data == 0 else data
    str_ea = [f'D{n}', f'A{n}', f'(A{n})', f'(A{n})+', f'-(A{n})', '({}' + f',A{n})', '{}', '{}', '{}'][ea]
    str_op = [f'ADDQ.B\t#{data},{str_ea}', f'ADDQ.W\t#{data},{str_ea}', f'ADDQ.L\t#{data},{str_ea}', None, f'SUBQ.B\t#{data},{str_ea}', f'SUBQ.W\t#{data},{str_ea}', f'SUBQ.L\t#{data},{str_ea}'][i >> 6 & 7]
    if size != 0 or ea != 1:
         table[0x5000 | i] = ('', str_op, *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
for i in range(0x1000):
    data = (lambda x : x & 0x7f | -(x & 0x80))(i)
    table[0x7000 | i] = ('', f'MOVEQ.L\t#${data:0=2x},D{i >> 9}' if data >= 0 else f'MOVEQ.L\t#-${-data:0=2x},D{i >> 9}')

# single operand
for i in range(0x100):
    size = i >> 6; ea = i >> 3 & 7; n = i & 7
    ea += n if ea == 7 else 0
    if ea == 1 or ea >= 9:
        continue
    str_ea = [f'D{n}', None, f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}'][ea]
    str_op = [f'.B\t{str_ea}', f'.W\t{str_ea}', f'.L\t{str_ea}', None][size]
    if size < 3:
        table[0x4000 | i] = ('', f'NEGX{str_op}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4200 | i] = ('', f'CLR{str_op}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4400 | i] = ('', f'NEG{str_op}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4600 | i] = ('', f'NOT{str_op}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
    if size == 0:
        table[0x4800 | i] = ('', f'NBCD.B {str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
    if size < 3:
        table[0x4a00 | i] = ('', f'TST{str_op}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
    if size == 3:
        table[0x4a00 | i] = ('', f'TAS.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5000 | i] = ('', f'ST.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5100 | i] = ('', f'SF.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5200 | i] = ('', f'SHI.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5300 | i] = ('', f'SLS.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5400 | i] = ('', f'SCC.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5500 | i] = ('', f'SCS.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5600 | i] = ('', f'SNE.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5700 | i] = ('', f'SEQ.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5800 | i] = ('', f'SVC.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5900 | i] = ('', f'SVS.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5a00 | i] = ('', f'SPL.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5b00 | i] = ('', f'SMI.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5c00 | i] = ('', f'SGE.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5d00 | i] = ('', f'SLT.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5e00 | i] = ('', f'SGT.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x5f00 | i] = ('', f'SLE.B\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))

# shift/rotate
for i in range(0x1000):
    y = i >> 9; dr = i >> 8 & 1; size = i >> 6 & 3;  n = i & 7
    str_dr_size = ['R.B', 'R.W', 'R.L', 'R.W', 'L.B', 'L.W', 'L.L', 'L.W'][dr * 4 + size]
    if size < 3:
        str_src = [f'#{y if y else 8}', f'D{y}'][i >> 5 & 1]
        str_op = [f'AS{str_dr_size}\t{str_src},D{n}', f'LS{str_dr_size}\t{str_src},D{n}', f'ROX{str_dr_size}\t{str_src},D{n}', f'RO{str_dr_size}\t{str_src},D{n}'][i >> 3 & 3]
        table[0xe000 | i] = ('', str_op)
    else:
        ea = i >> 3 & 7
        ea += n if ea == 7 else 0
        if y >= 4 or ea < 2 or ea >= 9:
            continue
        str_ea = [None, None, f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}'][ea]
        str_op = [f'AS{str_dr_size}\t{str_ea}', f'LS{str_dr_size}\t{str_ea}', f'ROX{str_dr_size}\t{str_ea}', f'RO{str_dr_size}\t{str_ea}'][y];
        table[0xe000 | i] = ('', str_op, *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))

# bit manipulation
for i in range(0x1000):
    y = i >> 9; dyn = i >> 8 & 1; op = i >> 6 & 3; ea = i >> 3 & 7; n = i & 7
    ea += n if ea == 7 else 0
    if not dyn and y != 4 or ea == 1 or ea >= 9:
        continue
    str_src = ['{}', f'D{y}'][dyn]
    str_ea = [f'D{n}', None, f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}'][ea]
    str_op = ['BTST', 'BCHG', 'BCLR', 'BSET'][op]
    str_size = '.L' if ea == 0 else '.B'
    table[0x0000 | i] = ('', f'{str_op}{str_size}\t{str_src},{str_ea}', *(([] if dyn else [am_immediate8]) + ([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else [])))

# branch
for i in range(0x100):
    n = i & 7
    if i:
        table[0x6000 | i] = ('AB', 'BRA\t{}', am_relative8)
        table[0x6100 | i] = ('B',  'BSR\t{}', am_relative8)
        table[0x6200 | i] = ('B',  'BHI\t{}', am_relative8)
        table[0x6300 | i] = ('B',  'BLS\t{}', am_relative8)
        table[0x6400 | i] = ('B',  'BCC\t{}', am_relative8)
        table[0x6500 | i] = ('B',  'BCS\t{}', am_relative8)
        table[0x6600 | i] = ('B',  'BNE\t{}', am_relative8)
        table[0x6700 | i] = ('B',  'BEQ\t{}', am_relative8)
        table[0x6800 | i] = ('B',  'BVC\t{}', am_relative8)
        table[0x6900 | i] = ('B',  'BVS\t{}', am_relative8)
        table[0x6a00 | i] = ('B',  'BPL\t{}', am_relative8)
        table[0x6b00 | i] = ('B',  'BMI\t{}', am_relative8)
        table[0x6c00 | i] = ('B',  'BGE\t{}', am_relative8)
        table[0x6d00 | i] = ('B',  'BLT\t{}', am_relative8)
        table[0x6e00 | i] = ('B',  'BGT\t{}', am_relative8)
        table[0x6f00 | i] = ('B',  'BLE\t{}', am_relative8)
    if (i >> 3 & 0x1f) == 0x19:
        table[0x5000 | i] = ('B',  f'DBT\tD{n},''{}', am_relative16)
        table[0x5100 | i] = ('B',  f'DBRA\tD{n},''{}', am_relative16)
        table[0x5200 | i] = ('B',  f'DBHI\tD{n},''{}', am_relative16)
        table[0x5300 | i] = ('B',  f'DBLS\tD{n},''{}', am_relative16)
        table[0x5400 | i] = ('B',  f'DBCC\tD{n},''{}', am_relative16)
        table[0x5500 | i] = ('B',  f'DBCS\tD{n},''{}', am_relative16)
        table[0x5600 | i] = ('B',  f'DBNE\tD{n},''{}', am_relative16)
        table[0x5700 | i] = ('B',  f'DBEQ\tD{n},''{}', am_relative16)
        table[0x5800 | i] = ('B',  f'DBVC\tD{n},''{}', am_relative16)
        table[0x5900 | i] = ('B',  f'DBVS\tD{n},''{}', am_relative16)
        table[0x5a00 | i] = ('B',  f'DBPL\tD{n},''{}', am_relative16)
        table[0x5b00 | i] = ('B',  f'DBMI\tD{n},''{}', am_relative16)
        table[0x5c00 | i] = ('B',  f'DBGE\tD{n},''{}', am_relative16)
        table[0x5d00 | i] = ('B',  f'DBLT\tD{n},''{}', am_relative16)
        table[0x5e00 | i] = ('B',  f'DBGT\tD{n},''{}', am_relative16)
        table[0x5f00 | i] = ('B',  f'DBLE\tD{n},''{}', am_relative16)

# JMP, JSR, LEA, PEA, MOVEM
for i in range(0x40):
    ea = i >> 3; n = i & 7
    ea += n if ea == 7 else 0
    if ea < 2 or ea >= 11:
        continue
    str_ea = [None, None, f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}', '({},PC)', '{}'][ea]
    if ea != 3 and ea != 4:
        table[0x41c0 | i] = ('',   f'LEA.L\t{str_ea},A0', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x43c0 | i] = ('',   f'LEA.L\t{str_ea},A1', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x45c0 | i] = ('',   f'LEA.L\t{str_ea},A2', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x47c0 | i] = ('',   f'LEA.L\t{str_ea},A3', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4840 | i] = ('',   f'PEA.L\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
    if ea != 3 and ea < 9:
        table[0x4880 | i] = ('',   'MOVEM.W\t{},'f'{str_ea}', register_list, *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x48c0 | i] = ('',   'MOVEM.L\t{},'f'{str_ea}', register_list, *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
    if ea != 3 and ea != 4:
        table[0x49c0 | i] = ('',   f'LEA.L\t{str_ea},A4', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4bc0 | i] = ('',   f'LEA.L\t{str_ea},A5', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
    if ea != 4:
        table[0x4c80 | i] = ('',   'MOVEM.W\t{}', movem)
        table[0x4cc0 | i] = ('',   'MOVEM.L\t{}', movem)
    if ea != 3 and ea != 4:
        table[0x4dc0 | i] = ('',   f'LEA.L\t{str_ea},A6', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4fc0 | i] = ('',   f'LEA.L\t{str_ea},A7', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4e80 | i] = ('B',  f'JSR\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x4ec0 | i] = ('AB', f'JMP\t{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))

# ADDX, CMPM. SUBX, ABCD, SBCD
for i in range(0x1000):
    x = i >> 9; size = i >> 6 & 3; rm = i >> 3 & 1; y = i & 7
    if (i & 0x130) != 0x100:
        continue
    str_size = ['.B', '.W', '.L', None][size]
    str_rm = [f'D{y},D{x}', f'-(A{y}),-(A{x})'][rm];
    if size == 0:
        table[0x8000 | i] = ('', f'SBCD.B\t{str_rm}')
    if size < 3:
        table[0x9000 | i] = ('', f'SUBX{str_size}\t{str_rm}')
    if size < 3 and rm:
        table[0xb000 | i] = ('', f'CMPM{str_size}\t(A{y})+,(A{x})+')
    if size == 0:
        table[0xc000 | i] = ('', f'ABCD.B\t{str_rm}')
    if size < 3:
        table[0xd000 | i] = ('', f'ADDX{str_size}\t{str_rm}')

# miscellaneous
for i in range(0x1000):
    x = i >> 9; ea = i >> 3 & 7; y = i & 7
    ea += y if ea == 7 else 0
    str_ea = [f'D{y}', None, f'(A{y})', f'(A{y})+', f'-(A{y})', '({},'f'A{y})', '{}', '{}', '{}', '({},PC)', '{}', '{}', None, None, None][ea]
    if (i >> 3 & 0x3f) == 0x21:
        table[0x0000 | i] = ('', 'MOVEP.W\t({}'f',A{y}),D{x}', displacement)
    if (i >> 3 & 0x3f) == 0x29:
        table[0x0000 | i] = ('', 'MOVEP.L\t({}'f',A{y}),D{x}', displacement)
    if (i >> 3 & 0x3f) == 0x31:
        table[0x0000 | i] = ('', f'MOVEP.W\tD{x},(''{}'f',A{y})', displacement)
    if (i >> 3 & 0x3f) == 0x39:
        table[0x0000 | i] = ('', f'MOVEP.L\tD{x},(''{}'f',A{y})', displacement)
    if (i >> 6 & 7) == 6 and ea != 1 and ea < 12:
        table[0x4000 | i] = ('', f'CHK.W\t{str_ea},D{x}', *([fnc_index[y]] if ea == 6 else [am_immediate16] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
    if (i >> 3 & 0x3f) == 0x28:
        table[0xc000 | i] = ('', f'EXG.L\tD{x},D{y}')
    if (i >> 3 & 0x3f) == 0x29:
        table[0xc000 | i] = ('', f'EXG.L\tA{x},A{y}')
    if (i >> 3 & 0x3f) == 0x31:
        table[0xc000 | i] = ('', f'EXG.L\tD{x},A{y}')
for i in range(0x40):
    ea = i >> 3; n = i & 7
    ea += n if ea == 7 else 0
    if ea == 1 or ea >= 12:
        continue
    str_ea = [f'D{n}', None, f'(A{n})', f'(A{n})+', f'-(A{n})', '({},'f'A{n})', '{}', '{}', '{}', '({},PC)', '{}', '{}'][ea]
    if ea != 1 and ea < 9:
        table[0x40c0 | i] = ('', f'MOVE.W\tSR,{str_ea}', *([fnc_index[n]] if ea == 6 else [fnc_ea[ea]] if ea >= 5 else []))
    if ea != 1:
        table[0x44c0 | i] = ('', f'MOVE.B\t{str_ea},CCR', *([fnc_index[n]] if ea == 6 else [am_immediate8] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
        table[0x46c0 | i] = ('', f'MOVE.W\t{str_ea},SR', *([fnc_index[n]] if ea == 6 else [am_immediate16] if ea == 11 else [fnc_ea[ea]] if ea >= 5 else []))
for n in range(8):
    table[0x4840 | n] = ('', f'SWAP.W\tD{n}')
    table[0x4880 | n] = ('', f'EXT.W\tD{n}')
    table[0x48c0 | n] = ('', f'EXT.L\tD{n}')
    table[0x4e50 | n] = ('', f'LINK.W\tA{n},#' +'{}', displacement)
    table[0x4e58 | n] = ('', f'UNLK\tA{n}')
    table[0x4e60 | n] = ('', f'MOVE.L\tA{n},USP')
    table[0x4e68 | n] = ('', f'MOVE.L\tUSP,A{n}')

def op():
    global flags, table
    opcode = fetch16()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[0]
    operands = [f() for f in t[2:]]
    return t[1].lower().format(*operands) if '' not in operands else ''

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
    buffer[start:] = data
    end = start + len(data)
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

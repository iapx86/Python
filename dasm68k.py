#
#   MC68000 disassembler
#

import functools
import getopt
import os
import sys

buffer = bytearray(0x1000000)
jumplabel = [False] * len(buffer)
label = [False] * len(buffer)
location = 0
flags = ''

s8 = lambda x : x & 0x7f | -(x & 0x80)
s16 = lambda x : x & 0x7fff | -(x & 0x8000)

def fetch():
    global buffer, location
    c = buffer[location]
    location += 1
    return c

def fetch16():
    return fetch() << 8 | fetch()

def fetch32():
    return fetch16() << 16 | fetch16()

def displacement():
    d = s16(fetch16())
    return f'-${-d:04x}' if d < 0 else f'${d:04x}'

def am_relative8():
    global jumplabel, buffer, location, flags
    ea = location + s8(buffer[location - 1]) & 0xffffff
    jumplabel[ea] = True
    return f'L{ea:06x}'

def am_relative16():
    global jumplabel, label, location, flags
    ea = location + s16(fetch16()) & 0xffffff
    if 'B' in flags:
        jumplabel[ea] = True
    else:
        label[ea] = True
    return f'L{ea:06x}'

def am_index(an):
    global label
    base = location; x = fetch16()
    if x & 0x700:
        return ''
    d = s8(x)
    rn = f'{"da"[x >> 15]}{x >> 12 & 7}.{"wl"[x >> 11 & 1]}'
    if an == 'pc':
        d = base + d & 0xffffff; label[d] = True
        return f'(L{d:06x},pc,{rn})'
    return f'(-${-d:02x},{an},{rn})' if d < 0 else f'(${d:02x},{an},{rn})' if d else f'({an},{rn})'

def am_absolute16():
    global jumplabel, label, flags
    x = s16(fetch16())
    ea = x & 0xffffff
    if ea < start or ea > end:
        return f'(-${-x:04x})' if x < 0 else f'(${x:04x})'
    if 'B' in flags:
        jumplabel[ea] = True
    else:
        label[ea] = True
    return f'(L{ea:06x}).w'

def am_absolute32():
    global jumplabel, label, flags
    x = fetch32()
    ea = x & 0xffffff
    if ea < start or ea > end:
        return f'(${x:08x}){"" if 0x8000 <= ea < 0xff8000 else ".l"}'
    if 'B' in flags:
        jumplabel[ea] = True
    else:
        label[ea] = True
    return f'(L{ea:06x})'

def am_immediate8():
    return f'#${fetch16() & 0xff:02x}'

def am_immediate16():
    global label, flags
    x = fetch16()
    ea = s16(x) & 0xffffff
    if 'P' in flags and ea >= start and ea <= end:
        label[ea] = True
        return f'#L{ea:06x}'
    return f'#${x:04x}'

def am_immediate32():
    global label, flags
    x = fetch16() << 16 | fetch16()
    ea = x & 0xffffff
    if 'P' in flags and ea >= start and ea <= end:
        label[ea] = True
        return f'#L{ea:06x}'
    return f'#${x:08x}'

def am_decode(mod, n, size=None):
    if mod >= 12:
        return None, None, []
    ea1 = (f'D{n}', f'A{n}', f'(A{n})', f'(A{n})+', f'-(A{n})', f'd(A{n})', f'd(A{n},Xi)', 'Abs.W', 'Abs.L', 'd(PC)', 'd(PC,Xi)', '#<data>')[mod]
    ea2 = (f'D{n}', f'A{n}', f'(A{n})', f'(A{n})+', f'-(A{n})', f'(%s,A{n})', '%s', '%s', '%s', '(%s,PC)', '%s', '%s')[mod]
    fnc_imm = {'B':am_immediate8, 'W':am_immediate16, 'L':am_immediate32}.get(size)
    fnc = {5:displacement, 6:lambda: am_index(f'a{n}'), 7:am_absolute16, 8:am_absolute32, 9:am_relative16, 10:lambda: am_index('pc'), 11:fnc_imm}.get(mod)
    return ea1, ea2, [fnc] if fnc else []

def branch16():
    global jumplabel, location, flags
    base = location
    d = s16(fetch16())
    ea = base + d & 0xffffff
    jumplabel[ea] = True
    return f'{".w" if -0x80 <= d < 0x80 else ""}\tL{ea:06x}'

def register_list():
    global buffer, location
    mod = buffer[location - 1] >> 3 & 7
    mask = f'{fetch16():016b}' if mod == 4 else f'{fetch16():016b}'[::-1]
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
    mod = buffer[location - 1] >> 3 & 7; n = buffer[location - 1] & 7; mod += n if mod == 7 else 0; ea1, ea2, fnc = am_decode(mod, n); regs = register_list()
    ea2 = functools.reduce(lambda a, b : a.replace('%s', b(), 1), fnc, ea2.lower())
    return f'{ea2},{regs}'

table = {
    0x4afc: ('ILLEGAL',   '',   'ILLEGAL'),
    0x4e70: ('RESET',     '',   'RESET'),
    0x4e71: ('NOP',       '',   'NOP'),
    0x4e72: ('STOP #xxx', '',   'STOP\t%s', am_immediate16),
    0x4e73: ('RTE',       'A',  'RTE'),
    0x4e75: ('RTS',       'A',  'RTS'),
    0x4e76: ('TRAPV',     '',   'TRAPV'),
    0x4e77: ('RTR',       'A',  'RTR'),
}

for i in range(0x1000):
    x = i >> 9 & 7; dst = i >> 6 & 7; src = i >> 3 & 7; y = i & 7; dst += x if dst == 7 else 0; src += y if src == 7 else 0
    if dst >= 9 or src >= 12:
        continue
    a, flg_a = ('A', 'P') if dst == 1 else ('', '')
    if dst != 1 and src != 1:
        src1, src2, fnc_src = am_decode(src, y, 'B'); dst1, dst2, fnc_dst = am_decode(dst, x)
        table[0x1000 | i] = (f'MOVE.B {src1},{dst1}', '', f'MOVE.B\t{src2},{dst2}', *fnc_src + fnc_dst)
    src1, src2, fnc_src = am_decode(src, y, 'W'); dst1, dst2, fnc_dst = am_decode(dst, x)
    table[0x3000 | i] = (f'MOVE{a}.W {src1},{dst1}', f'{flg_a}', f'MOVE{a}.W\t{src2},{dst2}', *fnc_src + fnc_dst)
    src1, src2, fnc_src = am_decode(src, y, 'L'); dst1, dst2, fnc_dst = am_decode(dst, x)
    table[0x2000 | i] = (f'MOVE{a}.L {src1},{dst1}', f'{flg_a}', f'MOVE{a}.L\t{src2},{dst2}', *fnc_src + fnc_dst)
for i in range(0x1000):
    x = i >> 9 & 7; op = i >> 6 & 7; mod = i >> 3 & 7; y = i & 7; mod += y if mod == 7 else 0
    if mod >= (12, 12, 12, 12, 9, 9, 9, 12)[op]:
        continue
    a = 'A' if op == 3 or op == 7 else ''; size = 'BWLWBWLL'[op]; ea1, ea2, fnc = am_decode(mod, y, size)
    ea1, ea2 = map(lambda y : {'S':f'{y},D{x}', 'D':f'D{x},{y}', 'A':f'{y},A{x}'}['SSSADDDA'[op]], (ea1, ea2))
    if op != 3 and op != 7 and mod != 1 and not (op >= 4 and op < 7 and mod == 0):
        table[0x8000 | i] = (f'OR.{size} {ea1}', '', f'OR.{size}\t{ea2}', *fnc)
        table[0xc000 | i] = (f'AND.{size} {ea1}', '', f'AND.{size}\t{ea2}', *fnc)
    if not (op == 0 and mod == 1) and not (op >= 4 and op < 7 and mod < 2):
        table[0x9000 | i] = (f'SUB{a}.{size} {ea1}', '', f'SUB{a}.{size}\t{ea2}', *fnc)
        table[0xd000 | i] = (f'ADD{a}.{size} {ea1}', '', f'ADD{a}.{size}\t{ea2}', *fnc)
    if not (op == 0 and mod == 1) and not (op >= 4 and op < 7):
        table[0xb000 | i] = (f'CMP{a}.{size} {ea1}', '', f'CMP{a}.{size}\t{ea2}', *fnc)
    if op >= 4 and op < 7 and mod != 1:
        table[0xb000 | i] = (f'EOR.{size} {ea1}', '', f'EOR.{size}\t{ea2}', *fnc)
    if (op == 3 or op == 7) and mod != 1:
        s = 'S' if op == 7 else 'U'; ea1, ea2, fnc = am_decode(mod, y, 'W')
        table[0x8000 | i] = (f'DIV{s}.W {ea1},D{x}', '', f'DIV{s}.W\t{ea2},D{x}', *fnc)
        table[0xc000 | i] = (f'MUL{s}.W {ea1},D{x}', '', f'MUL{s}.W\t{ea2},D{x}', *fnc)
for i in range(0xc0):
    mod = i >> 3 & 7; n = i & 7; mod += n if mod == 7 else 0
    if mod == 1 or mod >= 9:
        continue
    size = 'BWL'[i >> 6]; ea1, ea2, fnc = am_decode(mod, n); fnc = [{'B':am_immediate8, 'W':am_immediate16, 'L':am_immediate32}[size]] + fnc
    for base, op in {0x0000:'ORI', 0x0200:'ANDI', 0x0400:'SUBI', 0x0600:'ADDI', 0x0a00:'EORI', 0x0c00:'CMPI'}.items():
        table[base | i] = (f'{op}.{size} #<data>,{ea1}', '', f'{op}.{size}\t%s,{ea2}', *fnc)
for base, op, i, ea1 in [(base, op, i, ea1) for base, op in {0x0000:'ORI', 0x0200:'ANDI', 0x0a00:'EORI'}.items() for i, ea1 in {0x3c:'CCR', 0x7c:'SR'}.items()]:
    size = 'BW'[i >> 6]; fnc = [{'B':am_immediate8, 'W':am_immediate16}[size]]
    table[base | i] = (f'{op}.{size} #<data>,{ea1}', '', f'{op}.{size}\t%s,{ea1}', *fnc)
for i in range(0x1000):
    data = i >> 9 & 7; size = i >> 6 & 3; mod = i >> 3 & 7; n = i & 7; mod += n if mod == 7 else 0
    if size == 3 or mod >= 9 or size == 0 and mod == 1:
        continue
    op = ('ADDQ', 'SUBQ')[i >> 8 & 1]; size = 'BWL'[size]; data = data if data else 8; ea1, ea2, fnc = am_decode(mod, n)
    table[0x5000 | i] = (f'{op}.{size} #{data},{ea1}', '', f'{op}.{size}\t#{data},{ea2}', *fnc)
for i in range(0x1000):
    if i & 0x100:
        continue
    n = i >> 9; data = f'-${-s8(i):02x}' if i & 0x80 else f'${s8(i):02x}' 
    table[0x7000 | i] = (f'MOVEQ.L #{data},D{n}', '', f'MOVEQ.L\t#{data},D{n}')
for i in range(0xc0):
    mod = i >> 3 & 7; n = i & 7; mod += n if mod == 7 else 0
    if mod == 1 or mod >= 9:
        continue
    size = 'BWL'[i >> 6]; ea1, ea2, fnc = am_decode(mod, n)
    for base, op in {0x4000:'NEGX', 0x4200:'CLR', 0x4400:'NEG', 0x4600:'NOT', 0x4a00:'TST'}.items():
        table[base | i] = (f'{op}.{size} {ea1}', '', f'{op}.{size}\t{ea2}', *fnc)
    if size == 'B':
        table[0x4800 | i] = (f'NBCD.B {ea1}', '', f'NBCD.B\t{ea2}', *fnc)
for i in range(0xc0, 0x100):
    mod = i >> 3 & 7; n = i & 7; mod += n if mod == 7 else 0
    if mod == 1 or mod >= 9:
        continue
    ea1, ea2, fnc = am_decode(mod, n)
    for base, op in {0x4a00:'TAS', 0x5000:'ST', 0x5100:'SF', 0x5200:'SHI', 0x5300:'SLS', 0x5400:'SCC', 0x5500:'SCS', 0x5600:'SNE', 0x5700:'SEQ',
                     0x5800:'SVC', 0x5900:'SVS', 0x5a00:'SPL', 0x5b00:'SMI', 0x5c00:'SGE', 0x5d00:'SLT', 0x5e00:'SGT', 0x5f00:'SLE'}.items():
        table[base | i] = (f'{op}.B {ea1}', '', f'{op}.B\t{ea2}', *fnc)
for i in range(0x1000):
    y = i >> 9; dr = 'RL'[i >> 8 & 1]; size = i >> 6 & 3; n = i & 7
    if size < 3:
        size = 'BWL'[size]; src1 = (f'#{y if y else 8}', f'D{y}')[i >> 5 & 1]; op = ('AS', 'LS', 'ROX', 'RO')[i >> 3 & 3]
        table[0xe000 | i] = (f'{op}{dr}.{size} {src1},D{n}', '', f'{op}{dr}.{size}\t{src1},D{n}')
    else:
        mod = i >> 3 & 7; mod += n if mod == 7 else 0
        if y >= 4 or mod < 2 or mod >= 9:
            continue
        op = ('AS', 'LS', 'ROX', 'RO')[y]; ea1, ea2, fnc = am_decode(mod, n)
        table[0xe000 | i] = (f'{op}{dr}.W {ea1}', '', f'{op}{dr}.W\t{ea2}', *fnc)
for i in range(0x1000):
    y = i >> 9; dyn = i >> 8 & 1; mod = i >> 3 & 7; n = i & 7; mod += n if mod == 7 else 0
    if not dyn and y != 4 or mod == 1 or mod >= 9:
        continue
    src1 = ('#<data>', f'D{y}')[dyn]; src2 = ('%s', f'D{y}')[dyn]
    size = 'L' if mod == 0 else 'B'; ea1, ea2, fnc = am_decode(mod, n); fnc = ([] if dyn else [am_immediate8]) + fnc; op = ('BTST', 'BCHG', 'BCLR', 'BSET')[i >> 6 & 3]
    table[0x0000 | i] = (f'{op}.{size} {src1},{ea1}', '', f'{op}.{size}\t{src2},{ea2}', *fnc)
for i in range(0x100):
    n = i & 7
    table[0x6000 | i] = ('BRA.B <label>', 'AB', 'BRA\t%s', am_relative8) if i else ('BRA.W <label>', 'AB', 'BRA%s', branch16)
    for base, op in {0x6100:'BSR', 0x6200:'BHI', 0x6300:'BLS', 0x6400:'BCC', 0x6500:'BCS', 0x6600:'BNE', 0x6700:'BEQ', 0x6800:'BVC',
                        0x6900:'BVS', 0x6a00:'BPL', 0x6b00:'BMI', 0x6c00:'BGE', 0x6d00:'BLT', 0x6e00:'BGT', 0x6f00:'BLE'}.items():
        table[base | i] = (f'{op}.B <label>', 'B', f'{op}\t%s', am_relative8) if i else (f'{op}.W <label>', 'B', f'{op}%s', branch16)
    if (i >> 3 & 0x1f) == 0x19:
        for base, op in {0x5000:'DBT', 0x5100:'DBRA', 0x5200:'DBHI', 0x5300:'DBLS', 0x5400:'DBCC', 0x5500:'DBCS', 0x5600:'DBNE', 0x5700:'DBEQ', 
                         0x5800:'DBVC', 0x5900:'DBVS', 0x5a00:'DBPL', 0x5b00:'DBMI', 0x5c00:'DBGE', 0x5d00:'DBLT', 0x5e00:'DBGT', 0x5f00:'DBLE'}.items():
            table[base | i] = (f'{op} D{n},<label>', 'B', f'{op}\tD{n},%s', am_relative16)
for i in range(0x40):
    mod = i >> 3; n = i & 7; mod += n if mod == 7 else 0
    if mod < 2 or mod >= 11:
        continue
    ea1, ea2, fnc = am_decode(mod, n)
    if mod != 3 and mod != 4:
        for y in range(8):
            table[0x41c0 | y << 9 | i] = (f'LEA.L {ea1},A{y}', '', f'LEA.L\t{ea2},A{y}', *fnc)
        table[0x4840 | i] = (f'PEA.L {ea1}', '', f'PEA.L\t{ea2}', *fnc)
        table[0x4e80 | i] = (f'JSR {ea1}', 'B', f'JSR\t{ea2}', *fnc)
        table[0x4ec0 | i] = (f'JMP {ea1}', 'AB', f'JMP\t{ea2}', *fnc)
    if mod != 3 and mod < 9:
        table[0x4880 | i] = (f'MOVEM.W <register list>,{ea1}', '', f'MOVEM.W\t%s,{ea2}', register_list, *fnc)
        table[0x48c0 | i] = (f'MOVEM.L <register list>,{ea1}', '', f'MOVEM.L\t%s,{ea2}', register_list, *fnc)
    if mod != 4:
        table[0x4c80 | i] = (f'MOVEM.W {ea1},<register list>', '', 'MOVEM.W\t%s', movem)
        table[0x4cc0 | i] = (f'MOVEM.L {ea1},<register list>', '', 'MOVEM.L\t%s', movem)
for i in range(0x1000):
    x = i >> 9; size = i >> 6 & 3; rm = i >> 3 & 1; y = i & 7
    if (i & 0x130) != 0x100 or size == 3:
        continue
    size = 'BWL'[size]; rm1 = (f'D{y},D{x}', f'-(A{y}),-(A{x})')[rm]
    if size == 'B':
        table[0x8000 | i] = (f'SBCD.B {rm1}', '', f'SBCD.B\t{rm1}')
        table[0xc000 | i] = (f'ABCD.B {rm1}', '', f'ABCD.B\t{rm1}')
    if rm:
        table[0xb000 | i] = (f'CMPM.{size} (A{y})+,(A{x})+', '', f'CMPM.{size}\t(A{y})+,(A{x})+')
    table[0x9000 | i] = (f'SUBX.{size} {rm1}', '', f'SUBX.{size}\t{rm1}')
    table[0xd000 | i] = (f'ADDX.{size} {rm1}', '', f'ADDX.{size}\t{rm1}')
for i in range(0x1000):
    x = i >> 9; mod = i >> 3 & 7; y = i & 7; mod += y if mod == 7 else 0
    if (i >> 3 & 0x3f) == 0x21:
        table[0x0000 | i] = (f'MOVEP.W d(A{y}),D{x}', '', f'MOVEP.W\t(%s,A{y}),D{x}', displacement)
    if (i >> 3 & 0x3f) == 0x29:
        table[0x0000 | i] = (f'MOVEP.L d(A{y}),D{x}', '', f'MOVEP.L\t(%s,A{y}),D{x}', displacement)
    if (i >> 3 & 0x3f) == 0x31:
        table[0x0000 | i] = (f'MOVEP.W D{x},d(A{y})', '', f'MOVEP.W\tD{x},(%s,A{y})', displacement)
    if (i >> 3 & 0x3f) == 0x39:
        table[0x0000 | i] = (f'MOVEP.L D{x},d(A{y})', '', f'MOVEP.L\tD{x},(%s,A{y})', displacement)
    if (i >> 6 & 7) == 6 and mod != 1 and mod < 12:
        ea1, ea2, fnc = am_decode(mod, y, 'W')
        table[0x4000 | i] = (f'CHK.W {ea1},D{x}', '', f'CHK.W\t{ea2},D{x}', *fnc)
    if (i >> 3 & 0x3f) == 0x28:
        table[0xc000 | i] = (f'EXG.L D{x},D{y}', '', f'EXG.L\tD{x},D{y}')
    if (i >> 3 & 0x3f) == 0x29:
        table[0xc000 | i] = (f'EXG.L A{x},A{y}', '', f'EXG.L\tA{x},A{y}')
    if (i >> 3 & 0x3f) == 0x31:
        table[0xc000 | i] = (f'EXG.L D{x},A{y}', '', f'EXG.L\tD{x},A{y}')
for i in range(0x40):
    mod = i >> 3; n = i & 7; mod += n if mod == 7 else 0
    if mod == 1 or mod >= 12:
        continue
    ea1, ea2, fnc = am_decode(mod, n, 'W')
    if mod != 1 and mod < 9:
        table[0x40c0 | i] = (f'MOVE.W SR,{ea1}', '', f'MOVE.W\tSR,{ea2}', *fnc)
    if mod != 1:
        table[0x44c0 | i] = (f'MOVE.W {ea1},CCR', '', f'MOVE.W\t{ea2},CCR', *fnc)
        table[0x46c0 | i] = (f'MOVE.W {ea1},SR', '', f'MOVE.W\t{ea2},SR', *fnc)
for n in range(8):
    table[0x4840 | n] = (f'SWAP.W D{n}', '', f'SWAP.W\tD{n}')
    table[0x4880 | n] = (f'EXT.W D{n}', '', f'EXT.W\tD{n}')
    table[0x48c0 | n] = (f'EXT.L D{n}', '', f'EXT.L\tD{n}')
    table[0x4e50 | n] = (f'LINK A{n},#<displacement>', '', f'LINK.W\tA{n},#%s', displacement)
    table[0x4e58 | n] = (f'UNLK A{n}', '', f'UNLK\tA{n}')
    table[0x4e60 | n] = (f'MOVE.L A{n},USP', '', f'MOVE.L\tA{n},USP')
    table[0x4e68 | n] = (f'MOVE.L USP,A{n}', '', f'MOVE.L\tUSP,A{n}')
for v in range(16):
    table[0x4e40 | v] = (f'TRAP #{v}', '', f'TRAP\t#{v}')

def op():
    global flags, table
    opcode = fetch16()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[1]
    operands = [f() for f in t[3:]]
    return functools.reduce(lambda a, b : a.replace('%s', b, 1), operands, t[2].lower()) if '' not in operands else ''

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
attrib = bytearray(len(buffer))
start = 0
listing = False
force = False
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
        force = True
    elif o == '-l':
        listing = True
    elif o == '-o':
        file = open(a, 'w', encoding='utf-8')
    elif o == '-s':
        start = int(a, 0)
    elif o == '-t':
        tablefile = open(a, 'r', encoding='utf-8')
with open(args[0], 'rb') as f:
    data = f.read()[:len(buffer) - start]; end = start + len(data)
    buffer[start:end] = data
if tablefile:
    for line in tablefile:
        words = line.split(' ')
        if words[0] == 'b':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            attrib[base:base + size] = b'B' * size
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
            attrib[base:base + size] = b'S' * size
        elif words[0] == 't':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 4, 4):
                attrib[i:i + 4] = b'PPPP'
                jumplabel[int.from_bytes(buffer[i + 1:i + 4], 'big')] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 4, 4):
                attrib[i:i + 4] = b'PPPP'
                label[int.from_bytes(buffer[i + 1:i + 4], 'big')] = True

# path 1
if noentry and start == 0:
    label[start] = True
    reset = int.from_bytes(buffer[5:8], 'big')
    entry = reset if reset >= max(start, 8) and reset < end and not reset & 1 else start
    jumplabel[entry] = True
    for i in range(8, min(reset, 0x400), 4):
        vector = int.from_bytes(buffer[i + 1:i + 4], 'big')
        if vector >= max(start, 8) and vector < end and not vector & 1:
            jumplabel[vector] = True
elif noentry:
    entry = start
    jumplabel[entry] = True
while (location := next((start + i * 2 for i, (a, l) in enumerate(zip(attrib[start:end:2], jumplabel[start:end:2])) if not a and l), end)) != end:
    while True:
        base = location
        op()
        attrib[base:location] = b'C' * (location - base)
        if not force and 'A' in flags or location >= end or attrib[location]:
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
                print(f'{base:06X}\t\t\t', end='', file=file)
            print(f';{s}', file=file)
    if attrib[base] == b'C'[0]:
        s = op(); size = location - base
        if jumplabel[base]:
            if listing:
                print(f'{base:06X}\t\t\t\t', end='', file=file)
            print(f'L{base:06x}:', file=file)
        if listing:
            print(f'{base:06X}' + ''.join([' ' * (~i & 1) + f'{c:02X}' for i, c in enumerate(buffer[base:location])]) + '\t' * (33 - size // 2 * 5 >> 3), end='', file=file)
        print(f'\t{s}' if s else '\t.dc.b\t' + ','.join([f'${c:02x}' for c in buffer[base:location]]), file=file)
    elif attrib[base] == b'S'[0]:
        if label[base]:
            if listing:
                print(f'{base:06X}\t\t\t\t', end='', file=file)
            print(f'L{base:06x}:', file=file)
        if listing:
            print(f'{base:06X}\t\t\t\t', end='', file=file)
        print(f'\t.dc.b\t\'{fetch():c}', end='', file=file)
        while location < end and attrib[location] == b'S'[0] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif attrib[base] == b'B'[0]:
        if label[base]:
            if listing:
                print(f'{base:06X}\t\t\t\t', end='', file=file)
            print(f'L{base:06x}:', file=file)
        if listing:
            print(f'{base:06X}\t\t\t\t', end='', file=file)
        print(f'\t.dc.b\t${fetch():02x}', end='', file=file)
        for i in range(7):
            if location >= end or attrib[location] != b'B'[0] or label[location]:
                break
            print(f',${fetch():02x}', end='', file=file)
        print('', file=file)
    elif attrib[base] == b'P'[0]:
        if label[base]:
            if listing:
                print(f'{base:06X}\t\t\t\t', end='', file=file)
            print(f'L{base:06x}:', file=file)
        if listing:
            print(f'{base:06X}\t\t\t\t', end='', file=file)
        print(f'\t.dc.l\tL{fetch32():06x}', end='', file=file)
        for i in range(3):
            if location >= end or attrib[location] != b'P'[0] or label[location]:
                break
            print(f',L{fetch32():06x}', end='', file=file)
        print('', file=file)
    else:
        if label[base] or jumplabel[base]:
            if listing:
                print(f'{base:06X}\t\t\t\t', end='', file=file)
            print(f'L{base:06x}:', file=file)
        if listing:
            print(f'{base:06X}\t\t\t\t', end='', file=file)
        print(f'\t.dc.b\t${fetch():02x}', end='', file=file)
        for i in range(7):
            if location >= end or attrib[location] in b'CSBP' or label[location] or jumplabel[base]:
                break
            print(f',${fetch():02x}', end='', file=file)
        print('', file=file)
if label[location] or jumplabel[location]:
    if listing:
        print(f'{location:06X}\t\t\t\t', end='', file=file)
    print(f'L{location:06x}:', file=file)
if listing:
    print(f'{location & 0xffffff:06X}\t\t\t\t', end='', file=file)
print(f'\t.end\tL{entry:06x}', file=file)

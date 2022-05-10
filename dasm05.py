#
#   MC6805 disassembler
#

import getopt
import os
import sys

buffer = bytearray(0x10000)
jumplabel = [False] * 0x10000
label = [False] * 0x10000
location = 0
opcode = 0
flags = ''

def fetch():
    global buffer, location
    c = buffer[location]
    location += 1
    return c

def byte():
    return f'${fetch():0=2x}'

def word():
    global jumplabel, label, flags
    operand = fetch() << 8 | fetch()
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def am_relative():
    global jumplabel, label, location, flags
    operand = (lambda x : x & 0x7f | -(x & 0x80))(fetch()) + location & 0xffff
    jumplabel[operand] = True
    return f'L{operand:0=4x}'

table = {
    0x20: ('BRA',          'AB', 'BRA\t{}',         am_relative),
    0x21: ('BRN',          'B',  'BRN\t{}',         am_relative),
    0x22: ('BHI',          'B',  'BHI\t{}',         am_relative),
    0x23: ('BLS',          'B',  'BLS\t{}',         am_relative),
    0x24: ('BCC',          'B',  'BCC\t{}',         am_relative),
    0x25: ('BLO(BCS)',     'B',  'BCS\t{}',         am_relative),
    0x26: ('BNE',          'B',  'BNE\t{}',         am_relative),
    0x27: ('BEQ',          'B',  'BEQ\t{}',         am_relative),
    0x28: ('BHCC',         'B',  'BHCC\t{}',        am_relative),
    0x29: ('BHCS',         'B',  'BHCS\t{}',        am_relative),
    0x2a: ('BPL',          'B',  'BPL\t{}',         am_relative),
    0x2b: ('BMI',          'B',  'BMI\t{}',         am_relative),
    0x2c: ('BMC',          'B',  'BMC\t{}',         am_relative),
    0x2d: ('BMS',          'B',  'BMS\t{}',         am_relative),
    0x2e: ('BIL',          'B',  'BIL\t{}',         am_relative),
    0x2f: ('BIH',          'B',  'BIH\t{}',         am_relative),
    0x80: ('RTI',          'A',  'RTI'),
    0x81: ('RTS',          'A',  'RTS'),
    0x83: ('SWI',          '',   'SWI'),
    0x8e: ('STOP',         '',   'STOP'),
    0x8f: ('WAIT',         '',   'WAIT'),
    0x97: ('TAX',          '',   'TAX'),
    0x98: ('CLC',          '',   'CLC'),
    0x99: ('SEC',          '',   'SEC'),
    0x9a: ('CLI',          '',   'CLI'),
    0x9b: ('SEI',          '',   'SEI'),
    0x9c: ('RSP',          '',   'RSP'),
    0x9d: ('NOP',          '',   'NOP'),
    0x9f: ('TXA',          '',   'TXA'),
    0xad: ('BSR',          'B',  'BSR\t{}',         am_relative),
    0xbc: ('JMP <n',       'AB', 'JMP\t<{}',        byte),
    0xbd: ('JSR <n',       'B',  'JSR\t<{}',        byte),
    0xcc: ('JMP >nn',      'AB', 'JMP\t{}',         word),
    0xcd: ('JSR >nn',      'B',  'JSR\t{}',         word),
    0xdc: ('JMP nn,X',     'AB', 'JMP\t{},X',       word),
    0xdd: ('JSR nn,X',     'B',  'JSR\t{},X',       word),
    0xec: ('JMP n,X',      'AB', 'JMP\t{},X',       byte),
    0xed: ('JSR n,X',      'B',  'JSR\t{},X',       byte),
    0xfc: ('JMP ,X',       'AB', 'JMP\t,X'),
    0xfd: ('JSR ,X',       'B',  'JSR\t,X'),
}

for i, (op, b) in enumerate([(op, b) for b in range(8) for op in ('BRSET', 'BRCLR')]):
    table[0x00 | i] = (f'{op}{b}', 'B', f'{op}\t{b},''<{},{}', byte, am_relative)
for i, (op, b) in enumerate([(op, b) for b in range(8) for op in ('BSET', 'BCLR')]):
    table[0x10 | i] = (f'{op}{b}', '', f'{op}\t{b},''<{}', byte)
for i, op in {0:'NEG', 3:'COM', 4:'LSR', 6:'ROR', 7:'ASR', 8:'ASL', 9:'ROL', 0xa:'DEC', 0xc:'INC', 0xd:'TST', 0xf:'CLR'}.items():
    table[0x30 | i] = (f'{op} <n', '', f'{op}\t''<{}', byte)
    table[0x40 | i] = (f'{op}A', '', f'{op}A')
    table[0x50 | i] = (f'{op}X', '', f'{op}X')
    table[0x60 | i] = (f'{op} n,X', '', f'{op}\t''{},X', byte)
    table[0x70 | i] = (f'{op} ,X', '', f'{op}\t,X')
for i, op in {0:'SUB', 1:'CMP', 2:'SBC', 3:'CPX', 4:'AND', 5:'BIT', 6:'LDA', 8:'EOR', 9:'ADC', 0xa:'ORA', 0xb:'ADD', 0xe:'LDX'}.items():
    table[0xa0 | i] = (f'{op} #n', '', f'{op}\t''#{}', byte)
for i, op in {0:'SUB', 1:'CMP', 2:'SBC', 3:'CPX', 4:'AND', 5:'BIT', 6:'LDA', 7:'STA', 8:'EOR', 9:'ADC', 0xa:'ORA', 0xb:'ADD', 0xe:'LDX', 0xf:'STX'}.items():
    table[0xb0 | i] = (f'{op} <n', '', f'{op}\t''<{}', byte)
    table[0xc0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)
    table[0xd0 | i] = (f'{op} nn,X', '', f'{op}\t''{},X', word)
    table[0xe0 | i] = (f'{op} n,X', '', f'{op}\t''{},X', byte)
    table[0xf0 | i] = (f'{op} ,X', '', f'{op}\t,X')

def op():
    global flags, table
    opcode = fetch()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[1]
    return t[2].lower().format(*[f() for f in t[3:]])

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
code = [False] * 0x10000
string = [False] * 0x10000
bytestring = [False] * 0x10000
pointer = [False] * 0x10000
start = 0
end = 0
listing = False
noentry = True
file = sys.stdout
tablefile = None
for o, a in opts:
    if o == '-e':
        jumplabel[int(a, 0)] = True
        noentry = False
    elif o == '-f':
        code = [True] * 0x10000
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
    end = min(start + len(data), 0x10000)
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
            for i in range(base, base + size * 2, 2):
                pointer[i:i + 2] = [True] * 2
                jumplabel[buffer[i] << 8 | buffer[i + 1]] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 2, 2):
                pointer[i:i + 2] = [True] * 2
                label[buffer[i] << 8 | buffer[i + 1]] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 3, 3):
                pointer[i:i + 2] = [True] * 2
                label[buffer[i] << 8 | buffer[i + 1]] = True

# path 1
if noentry:
    jumplabel[start] = True
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
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t*\tMC6805 disassembler', file=file)
    print(f'\t\t\t*\tfilename: {args[0]}', file=file)
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t\torg\t${start:0=4x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMC6805 disassembler', file=file)
    print(f'*\tfilename: {args[0]}', file=file)
    print(f'************************************************', file=file)
    print(f'\torg\t${start:0=4x}', file=file)
    print(f'', file=file)
location = start
while location < end:
    base = location
    if base in remark:
        for s in remark[base]:
            if listing:
                print(f'{base:0=4X}\t\t\t', end='', file=file)
            print(f'*{s}', file=file)
    if code[base]:
        s = op()
        size = location - base
    else:
        s = ''
        size = 1
    if s != '':
        if listing:
            print(f'{base:0=4X} ', end='', file=file)
            location = base
            for i in range(size):
                print(f' {fetch():0=2X}', end='', file=file)
            print('\t\t' if size < 4 else '\t', end='', file=file)
        if jumplabel[base]:
            print(f'L{base:0=4x}', end='', file=file)
        print('\t' + s, file=file)
    elif string[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}', end='', file=file)
        location = base
        print(f'\tfcc\t\'{fetch():c}', end='', file=file)
        while location < end and string[location] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif bytestring[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}', end='', file=file)
        location = base
        print(f'\tfcb\t${fetch():0=2x}', end='', file=file)
        for i in range(7):
            if location >= end or not bytestring[location] or label[location]:
                break
            print(f',${fetch():0=2x}', end='', file=file)
        print('', file=file)
    elif pointer[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}', end='', file=file)
        location = base
        print(f'\tfdb\tL{fetch() << 8 | fetch():0=4x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch() << 8 | fetch():0=4x}', end='', file=file)
        print('', file=file)
    else:
        location = base
        for i in range(size):
            base = location
            c = fetch()
            if listing:
                print(f'{base:0=4X}  {c:0=2X}\t\t', end='', file=file)
            if label[base] or jumplabel[base]:
                print(f'L{base:0=4x}', end='', file=file)
            print(f'\tfcb\t${c:0=2x}', end='', file=file)
            if c >= 0x20 and c < 0x7f:
                print(f'\t\'{c:c}\'', end='', file=file)
            print('', file=file)
if listing:
    print(f'{location & 0xffff:0=4X}\t\t\t', end='', file=file)
print('\tend', file=file)

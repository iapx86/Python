#
#   MCS6502 disassembler
#

import getopt
import os
import sys

buffer = bytearray(0x10000)
jumplabel = [False] * len(buffer)
label = [False] * len(buffer)
location = 0
flags = ''

def fetch():
    global buffer, location
    c = buffer[location]
    location += 1
    return c

def byte():
    return f'${fetch():02x}'

def word():
    global jumplabel, label, flags
    operand = fetch() | fetch() << 8
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:04x}'

def am_relative():
    global jumplabel, label, location, flags
    operand = (lambda x : x & 0x7f | -(x & 0x80))(fetch()) + location & 0xffff
    jumplabel[operand] = True
    return f'L{operand:04x}'

table = {
    0x00: ('BRK',       '',   'BRK\t{}',     byte),
    0x08: ('PHP',       '',   'PHP'),
    0x10: ('BPL',       'B',  'BPL\t{}',     am_relative),
    0x18: ('CLC',       '',   'CLC'),
    0x20: ('JSR nn',    'B',  'JSR\t{}',     word),
    0x28: ('PLP',       '',   'PLP'),
    0x30: ('BMI',       'B',  'BMI\t{}',     am_relative),
    0x38: ('SEC',       '',   'SEC'),
    0x40: ('RTI',       'A',  'RTI'),
    0x48: ('PHA',       '',   'PHA'),
    0x4c: ('JMP nn',    'AB', 'JMP\t{}',     word),
    0x50: ('BVC',       'B',  'BVC\t{}',     am_relative),
    0x58: ('CLI',       '',   'CLI'),
    0x60: ('RTS',       'A',  'RTS'),
    0x68: ('PLA',       '',   'PLA'),
    0x6c: ('JMP (nn)',  'A',  'JMP\t({})',   word),
    0x70: ('BVS',       'B',  'BVS\t{}',     am_relative),
    0x78: ('SEI',       '',   'SEI'),
    0x88: ('DEY',       '',   'DEY'),
    0x8a: ('TXA',       '',   'TXA'),
    0x90: ('BCC',       'B',  'BCC\t{}',     am_relative),
    0x94: ('STY n,X',   '',   'STY\t{},X',   byte),
    0x96: ('STX n,Y',   '',   'STX\t{},Y',   byte),
    0x98: ('TYA',       '',   'TYA'),
    0x9a: ('TXS',       '',   'TXS'),
    0xa8: ('TAY',       '',   'TAY'),
    0xaa: ('TAX',       '',   'TAX'),
    0xb0: ('BCS',       'B',  'BCS\t{}',     am_relative),
    0xb4: ('LDY n,X',   '',   'LDY\t{},X',   byte),
    0xb6: ('LDX n,Y',   '',   'LDX\t{},Y',   byte),
    0xb8: ('CLV',       '',   'CLV'),
    0xba: ('TSX',       '',   'TSX'),
    0xbc: ('LDY nn,X',  '',   'LDY\t{},X',   word),
    0xbe: ('LDX nn,Y',  '',   'LDX\t{},Y',   word),
    0xc8: ('INY',       '',   'INY'),
    0xca: ('DEX',       '',   'DEX'),
    0xd0: ('BNE',       'B',  'BNE\t{}',     am_relative),
    0xd8: ('CLD',       '',   'CLD'),
    0xe8: ('INX',       '',   'INX'),
    0xea: ('NOP',       '',   'NOP'),
    0xf0: ('BEQ',       'B',  'BEQ\t{}',     am_relative),
    0xf8: ('SED',       '',   'SED'),
}

for i, op in {0x01:'ORA', 0x21:'AND', 0x41:'EOR', 0x61:'ADC', 0x81:'STA', 0xa1:'LDA', 0xc1:'CMP', 0xe1:'SBC'}.items():
    table[0x00 | i] = (f'{op} (n,X)', '', f'{op}\t''({},X)', byte)
    table[0x10 | i] = (f'{op} (n),Y', '', f'{op}\t''({}),Y', byte)
    table[0x18 | i] = (f'{op} nn,Y', '', f'{op}\t''{},Y', word)
for i, op in {0x01:'ORA', 0x02:'ASL', 0x21:'AND', 0x22:'ROL', 0x41:'EOR', 0x42:'LSR', 0x61:'ADC', 0x62:'ROR', 0x81:'STA', 0xa1:'LDA', 0xc1:'CMP', 0xc2:'DEC', 0xe1:'SBC', 0xe2:'INC'}.items():
    table[0x04 | i] = (f'{op} n', '', f'{op}\t''{}', byte)
    table[0x0c | i] = (f'{op} nn', '', f'{op}\t''{}', word)
for i, op in {0x01:'ORA', 0x21:'AND', 0x41:'EOR', 0x61:'ADC', 0xa1:'LDA', 0xc1:'CMP', 0xe1:'SBC'}.items():
    table[0x08 | i] = (f'{op} #n', '', f'{op}\t''#{}', byte)
for i, op in {0x01:'ORA', 0x02:'ASL', 0x21:'AND', 0x22:'ROL', 0x41:'EOR', 0x42:'LSR', 0x61:'ADC', 0x62:'ROR', 0x81:'STA', 0xa1:'LDA', 0xc1:'CMP', 0xc2:'DEC', 0xe1:'SBC', 0xe2:'INC'}.items():
    table[0x14 | i] = (f'{op} n,X', '', f'{op}\t''{},X', byte)
    table[0x1c | i] = (f'{op} nn,X', '', f'{op}\t''{},X', word)
for i, op in {0xa0:'LDY', 0xa2:'LDX', 0xc0:'CPY', 0xe0:'CPX'}.items():
    table[0x00 | i] = (f'{op} #n', '', f'{op}\t''#{}', byte)
for i, op in {0x20:'BIT', 0x80:'STY', 0x82:'STX', 0xa0:'LDY', 0xa2:'LDX', 0xc0:'CPY', 0xe0:'CPX'}.items():
    table[0x04 | i] = (f'{op} n', '', f'{op}\t''{}', byte)
    table[0x0c | i] = (f'{op} nn', '', f'{op}\t''{}', word)
for i, op in {0x02:'ASL', 0x22:'ROL', 0x42:'LSR', 0x62:'ROR'}.items():
    table[0x08 | i] = (f'{op}A', '', f'{op}A')

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
code = [False] * len(buffer)
string = [False] * len(buffer)
bytestring = [False] * len(buffer)
pointer = [False] * len(buffer)
start = 0
listing = False
noentry = True
file = sys.stdout
tablefile = None
for o, a in opts:
    if o == '-e':
        jumplabel[int(a, 0)] = True
        noentry = False
    elif o == '-f':
        code = [True] * len(buffer)
    elif o == '-l':
        listing = True
    elif o == '-o':
        file = open(a, 'w', encoding='utf-8')
    elif o == '-s':
        start = int(a, 0)
    elif o == '-t':
        tablefile = open(a, 'r', encoding='utf-8')
with open(args[0], 'rb') as f:
    data = f.read()
    end = min(start + len(data), len(buffer))
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
                jumplabel[buffer[i] | buffer[i + 1] << 8] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 2, 2):
                pointer[i:i + 2] = [True] * 2
                label[buffer[i] | buffer[i + 1] << 8] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 3, 3):
                pointer[i:i + 2] = [True] * 2
                label[buffer[i] | buffer[i + 1] << 8] = True

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
    print(f'\t\t\t*\tMCS6502 disassembler', file=file)
    print(f'\t\t\t*\tfilename: {args[0]}', file=file)
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t\torg\t${start:04x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMCS6502 disassembler', file=file)
    print(f'*\tfilename: {args[0]}', file=file)
    print(f'************************************************', file=file)
    print(f'\torg\t${start:04x}', file=file)
    print(f'', file=file)
location = start
while location < end:
    base = location
    if base in remark:
        for s in remark[base]:
            if listing:
                print(f'{base:04X}\t\t\t', end='', file=file)
            print(f'*{s}', file=file)
    if code[base]:
        s = op()
        size = location - base
    else:
        s = ''
        size = 1
    if s != '':
        if listing:
            print(f'{base:04X} ', end='', file=file)
            location = base
            for i in range(size):
                print(f' {fetch():02X}', end='', file=file)
            print('\t\t' if size < 4 else '\t', end='', file=file)
        if jumplabel[base]:
            print(f'L{base:04x}', end='', file=file)
        print(f'\t{s}', file=file)
    elif string[base]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        location = base
        print(f'\tfcc\t\'{fetch():c}', end='', file=file)
        while location < end and string[location] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif bytestring[base]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        location = base
        print(f'\tfcb\t${fetch():02x}', end='', file=file)
        for i in range(7):
            if location >= end or not bytestring[location] or label[location]:
                break
            print(f',${fetch():02x}', end='', file=file)
        print('', file=file)
    elif pointer[base]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        location = base
        print(f'\tfdb\tL{fetch() | fetch() << 8:04x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch() | fetch() << 8:04x}', end='', file=file)
        print('', file=file)
    else:
        location = base
        for i in range(size):
            base = location
            c = fetch()
            if listing:
                print(f'{base:04X}  {c:02X}\t\t', end='', file=file)
            if label[base] or jumplabel[base]:
                print(f'L{base:04x}', end='', file=file)
            print(f'\tfcb\t${c:02x}', end='', file=file)
            if c >= 0x20 and c < 0x7f:
                print(f'\t\'{c:c}\'', end='', file=file)
            print('', file=file)
if listing:
    print(f'{location & 0xffff:04X}\t\t\t', end='', file=file)
print('\tend', file=file)

#
#   MCS6502 disassembler
#

import functools
import getopt
import os
import sys

buffer = bytearray(0x10000)
jumplabel = [False] * len(buffer)
label = [False] * len(buffer)
location = 0
flags = ''


def s8(x):
    return x & 0x7f | -(x & 0x80)


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
    operand = s8(fetch()) + location & 0xffff
    jumplabel[operand] = True
    return f'L{operand:04x}'


table = {
    0x00: ('BRK',       '',   'BRK\t%s',     byte),
    0x08: ('PHP',       '',   'PHP'),
    0x10: ('BPL',       'B',  'BPL\t%s',     am_relative),
    0x18: ('CLC',       '',   'CLC'),
    0x20: ('JSR nn',    'B',  'JSR\t%s',     word),
    0x28: ('PLP',       '',   'PLP'),
    0x30: ('BMI',       'B',  'BMI\t%s',     am_relative),
    0x38: ('SEC',       '',   'SEC'),
    0x40: ('RTI',       'A',  'RTI'),
    0x48: ('PHA',       '',   'PHA'),
    0x4c: ('JMP nn',    'AB', 'JMP\t%s',     word),
    0x50: ('BVC',       'B',  'BVC\t%s',     am_relative),
    0x58: ('CLI',       '',   'CLI'),
    0x60: ('RTS',       'A',  'RTS'),
    0x68: ('PLA',       '',   'PLA'),
    0x6c: ('JMP (nn)',  'A',  'JMP\t(%s)',   word),
    0x70: ('BVS',       'B',  'BVS\t%s',     am_relative),
    0x78: ('SEI',       '',   'SEI'),
    0x88: ('DEY',       '',   'DEY'),
    0x8a: ('TXA',       '',   'TXA'),
    0x90: ('BCC',       'B',  'BCC\t%s',     am_relative),
    0x94: ('STY n,X',   '',   'STY\t%s,X',   byte),
    0x96: ('STX n,Y',   '',   'STX\t%s,Y',   byte),
    0x98: ('TYA',       '',   'TYA'),
    0x9a: ('TXS',       '',   'TXS'),
    0xa8: ('TAY',       '',   'TAY'),
    0xaa: ('TAX',       '',   'TAX'),
    0xb0: ('BCS',       'B',  'BCS\t%s',     am_relative),
    0xb4: ('LDY n,X',   '',   'LDY\t%s,X',   byte),
    0xb6: ('LDX n,Y',   '',   'LDX\t%s,Y',   byte),
    0xb8: ('CLV',       '',   'CLV'),
    0xba: ('TSX',       '',   'TSX'),
    0xbc: ('LDY nn,X',  '',   'LDY\t%s,X',   word),
    0xbe: ('LDX nn,Y',  '',   'LDX\t%s,Y',   word),
    0xc8: ('INY',       '',   'INY'),
    0xca: ('DEX',       '',   'DEX'),
    0xd0: ('BNE',       'B',  'BNE\t%s',     am_relative),
    0xd8: ('CLD',       '',   'CLD'),
    0xe8: ('INX',       '',   'INX'),
    0xea: ('NOP',       '',   'NOP'),
    0xf0: ('BEQ',       'B',  'BEQ\t%s',     am_relative),
    0xf8: ('SED',       '',   'SED'),
}

for i, op in {0x01:'ORA', 0x21:'AND', 0x41:'EOR', 0x61:'ADC', 0x81:'STA', 0xa1:'LDA', 0xc1:'CMP', 0xe1:'SBC'}.items():
    table[0x00 | i] = (f'{op} (n,X)', '', f'{op}\t(%s,X)', byte)
    table[0x10 | i] = (f'{op} (n),Y', '', f'{op}\t(%s),Y', byte)
    table[0x18 | i] = (f'{op} nn,Y', '', f'{op}\t%s,Y', word)
for i, op in {0x01:'ORA', 0x02:'ASL', 0x21:'AND', 0x22:'ROL', 0x41:'EOR', 0x42:'LSR', 0x61:'ADC', 0x62:'ROR', 0x81:'STA', 0xa1:'LDA', 0xc1:'CMP', 0xc2:'DEC', 0xe1:'SBC', 0xe2:'INC'}.items():
    table[0x04 | i] = (f'{op} n', '', f'{op}\t%s', byte)
    table[0x0c | i] = (f'{op} nn', '', f'{op}\t%s', word)
for i, op in {0x01:'ORA', 0x21:'AND', 0x41:'EOR', 0x61:'ADC', 0xa1:'LDA', 0xc1:'CMP', 0xe1:'SBC'}.items():
    table[0x08 | i] = (f'{op} #n', '', f'{op}\t#%s', byte)
for i, op in {0x01:'ORA', 0x02:'ASL', 0x21:'AND', 0x22:'ROL', 0x41:'EOR', 0x42:'LSR', 0x61:'ADC', 0x62:'ROR', 0x81:'STA', 0xa1:'LDA', 0xc1:'CMP', 0xc2:'DEC', 0xe1:'SBC', 0xe2:'INC'}.items():
    table[0x14 | i] = (f'{op} n,X', '', f'{op}\t%s,X', byte)
    table[0x1c | i] = (f'{op} nn,X', '', f'{op}\t%s,X', word)
for i, op in {0xa0:'LDY', 0xa2:'LDX', 0xc0:'CPY', 0xe0:'CPX'}.items():
    table[0x00 | i] = (f'{op} #n', '', f'{op}\t#%s', byte)
for i, op in {0x20:'BIT', 0x80:'STY', 0x82:'STX', 0xa0:'LDY', 0xa2:'LDX', 0xc0:'CPY', 0xe0:'CPX'}.items():
    table[0x04 | i] = (f'{op} n', '', f'{op}\t%s', byte)
    table[0x0c | i] = (f'{op} nn', '', f'{op}\t%s', word)
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
    return functools.reduce(lambda a, b : a.replace('%s', b(), 1), t[3:], t[2].lower())


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
noentry = True
file = sys.stdout
tablefile = None
for o, a in opts:
    if o == '-e':
        jumplabel[int(a, 0)] = True
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
            for i in range(base, base + size * 2, 2):
                attrib[i:i + 2] = b'PP'
                jumplabel[buffer[i] | buffer[i + 1] << 8] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 2, 2):
                attrib[i:i + 2] = b'PP'
                label[buffer[i] | buffer[i + 1] << 8] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 3, 3):
                attrib[i:i + 2] = b'PP'
                label[buffer[i] | buffer[i + 1] << 8] = True

# path 1
if noentry:
    jumplabel[start] = True
while (location := next((start + i for i, (a, l) in enumerate(zip(attrib[start:end], jumplabel[start:end])) if not a and l), end)) != end:
    while True:
        base = location
        op()
        attrib[base:location] = b'C' * (location - base)
        if not force and 'A' in flags or location >= end or attrib[location]:
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
    if attrib[base] == b'C'[0]:
        s = op(); size = location - base
        if listing:
            print(f'{base:04X} ' + ''.join([f' {c:02X}' for c in buffer[base:location]]) + '\t' * (26 - size * 3 >> 3), end='', file=file)
        if jumplabel[base]:
            print(f'L{base:04x}', end='', file=file)
        print(f'\t{s}' if s else '\tfcb\t' + ','.join([f'${c:02x}' for c in buffer[base:location]]), file=file)
    elif attrib[base] == b'S'[0]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        location = next((base + 1 + i for i, (a, l) in enumerate(zip(attrib[base + 1:end], label[base + 1:end])) if a != b'S'[0] or l), end)
        print(f'\tfcc\t\'{buffer[base:location].decode()}\'', file=file)
    elif attrib[base] == b'B'[0]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        limit = min(base + 8, end)
        location = next((base + 1 + i for i, (a, l) in enumerate(zip(attrib[base + 1:limit], label[base + 1:limit])) if a != b'B'[0] or l), limit)
        print(f'\tfcb\t' + ','.join([f'${c:02x}' for c in buffer[base:location]]), file=file)
    elif attrib[base] == b'P'[0]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        limit = min(base + 8, end)
        location = next((base + 2 + i * 2 for i, (a, l) in enumerate(zip(attrib[base + 2:limit:2], label[base + 2:limit:2])) if a != b'P'[0] or l), limit)
        print(f'\tfdb\t' + ','.join([f'L{buffer[i + 1]:02x}{buffer[i]:02x}' for i in range(base, location, 2)]), file=file)
    else:
        c = fetch()
        if listing:
            print(f'{base:04X}  {c:02X}\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        print(f'\tfcb\t${c:02x}' + (f'\t\'{c:c}\'' if c >= 0x20 and c < 0x7f else ''), file=file)
if listing:
    print(f'{location & 0xffff:04X}\t\t\t', end='', file=file)
print('\tend', file=file)

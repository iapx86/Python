#
#   MC6805 disassembler
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

s8 = lambda x : x & 0x7f | -(x & 0x80)

def fetch():
    global buffer, location
    c = buffer[location]
    location += 1
    return c

def fetch16():
    return fetch() << 8 | fetch()

def byte():
    return f'${fetch():02x}'

def word():
    global jumplabel, label, flags
    operand = fetch16()
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
    0x20: ('BRA',      'AB', 'BRA\t%s',   am_relative),
    0x80: ('RTI',      'A',  'RTI'),
    0x81: ('RTS',      'A',  'RTS'),
    0x83: ('SWI',      '',   'SWI'),
    0x8e: ('STOP',     '',   'STOP'),
    0x8f: ('WAIT',     '',   'WAIT'),
    0xad: ('BSR',      'B',  'BSR\t%s',   am_relative),
    0xbc: ('JMP <n',   'AB', 'JMP\t<%s',  byte),
    0xbd: ('JSR <n',   'B',  'JSR\t<%s',  byte),
    0xcc: ('JMP >nn',  'AB', 'JMP\t%s',   word),
    0xcd: ('JSR >nn',  'B',  'JSR\t%s',   word),
    0xdc: ('JMP nn,X', 'AB', 'JMP\t%s,X', word),
    0xdd: ('JSR nn,X', 'B',  'JSR\t%s,X', word),
    0xec: ('JMP n,X',  'AB', 'JMP\t%s,X', byte),
    0xed: ('JSR n,X',  'B',  'JSR\t%s,X', byte),
    0xfc: ('JMP ,X',   'AB', 'JMP\t,X'),
    0xfd: ('JSR ,X',   'B',  'JSR\t,X'),
}

for i, (op, b) in enumerate([(op, b) for b in range(8) for op in ('BRSET', 'BRCLR')]):
    table[0x00 | i] = (f'{op}{b}', 'B', f'{op}\t{b},<%s,%s', byte, am_relative)
for i, (op, b) in enumerate([(op, b) for b in range(8) for op in ('BSET', 'BCLR')]):
    table[0x10 | i] = (f'{op}{b}', '', f'{op}\t{b},<%s', byte)
for i, op in {1:'BRN', 2:'BHI', 3:'BLS', 4:'BCC', 5:'BCS', 6:'BNE', 7:'BEQ', 8:'BHCC', 9:'BHCS', 0xa:'BPL', 0xb:'BMI', 0xc:'BMC', 0xd:'BMS', 0xe:'BIL', 0xf:'BIH'}.items():
    table[0x20 | i] = (f'{op}', 'B', f'{op}\t%s', am_relative)
for i, op in {0:'NEG', 3:'COM', 4:'LSR', 6:'ROR', 7:'ASR', 8:'ASL', 9:'ROL', 0xa:'DEC', 0xc:'INC', 0xd:'TST', 0xf:'CLR'}.items():
    table[0x30 | i] = (f'{op} <n', '', f'{op}\t<%s', byte)
    table[0x40 | i] = (f'{op}A', '', f'{op}A')
    table[0x50 | i] = (f'{op}X', '', f'{op}X')
    table[0x60 | i] = (f'{op} n,X', '', f'{op}\t%s,X', byte)
    table[0x70 | i] = (f'{op} ,X', '', f'{op}\t,X')
for i, op in {7:'TAX', 8:'CLC', 9:'SEC', 0xa:'CLI', 0xb:'SEI', 0xc:'RSP', 0xd:'NOP', 0xf:'TXA'}.items():
    table[0x90 | i] = (f'{op}', '', f'{op}')
for i, op in {0:'SUB', 1:'CMP', 2:'SBC', 3:'CPX', 4:'AND', 5:'BIT', 6:'LDA', 8:'EOR', 9:'ADC', 0xa:'ORA', 0xb:'ADD', 0xe:'LDX'}.items():
    table[0xa0 | i] = (f'{op} #n', '', f'{op}\t#%s', byte)
for i, op in {0:'SUB', 1:'CMP', 2:'SBC', 3:'CPX', 4:'AND', 5:'BIT', 6:'LDA', 7:'STA', 8:'EOR', 9:'ADC', 0xa:'ORA', 0xb:'ADD', 0xe:'LDX', 0xf:'STX'}.items():
    table[0xb0 | i] = (f'{op} <n', '', f'{op}\t<%s', byte)
    table[0xc0 | i] = (f'{op} >nn', '', f'{op}\t%s', word)
    table[0xd0 | i] = (f'{op} nn,X', '', f'{op}\t%s,X', word)
    table[0xe0 | i] = (f'{op} n,X', '', f'{op}\t%s,X', byte)
    table[0xf0 | i] = (f'{op} ,X', '', f'{op}\t,X')

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
                jumplabel[buffer[i] << 8 | buffer[i + 1]] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 2, 2):
                attrib[i:i + 2] = b'PP'
                label[buffer[i] << 8 | buffer[i + 1]] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 3, 3):
                attrib[i:i + 2] = b'PP'
                label[buffer[i] << 8 | buffer[i + 1]] = True

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
    print(f'\t\t\t*\tMC6805 disassembler', file=file)
    print(f'\t\t\t*\tfilename: {args[0]}', file=file)
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t\torg\t${start:04x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMC6805 disassembler', file=file)
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
        print(f'\tfcc\t\'{fetch():c}', end='', file=file)
        while location < end and attrib[location] == b'S'[0] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif attrib[base] == b'B'[0]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        print(f'\tfcb\t${fetch():02x}', end='', file=file)
        for i in range(7):
            if location >= end or attrib[location] != b'B'[0] or label[location]:
                break
            print(f',${fetch():02x}', end='', file=file)
        print('', file=file)
    elif attrib[base] == b'P'[0]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}', end='', file=file)
        print(f'\tfdb\tL{fetch16():04x}', end='', file=file)
        for i in range(3):
            if location >= end or attrib[location] != b'P'[0] or label[location]:
                break
            print(f',L{fetch16():04x}', end='', file=file)
        print('', file=file)
    else:
        c = fetch()
        if listing:
            print(f'{base:04X}  {c:02X}\t\t', end='', file=file)
        if label[base] or jumplabel[base]:
            print(f'L{base:04x}', end='', file=file)
        print(f'\tfcb\t${c:02x}' + (f'\t\'{c:c}\'' if c >= 0x20 and c < 0x7f else ''), file=file)
if listing:
    print(f'{location & 0xffff:04X}\t\t\t', end='', file=file)
print('\tend', file=file)

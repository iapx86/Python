#
#   MCS6502 disassembler
#

import getopt
import os
import sys

buffer = bytearray(0x10000)
jumplabel = [False] * 0x10000
label = [False] * 0x10000
location = 0
table = None
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
    operand = fetch() | fetch() << 8
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def am_relative():
    global jumplabel, label, location, flags
    operand = (lambda x : x & 0x7f | -(x & 0x80))(fetch()) + location & 0xffff
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

table = {
0x00: # BRK
    ('',   'BRK\t{}',     byte),
0x01: # ORA (n,X)
    ('',   'ORA\t({},X)', byte),
0x05: # ORA n
    ('',   'ORA\t{}',     byte),
0x06: # ASL n
    ('',   'ASL\t{}',     byte),
0x08: # PHP
    ('',   'PHP'),
0x09: # ORA #n
    ('',   'ORA\t#{}',    byte),
0x0a: # ASLA
    ('',   'ASLA'),
0x0d: # ORA nn
    ('',   'ORA\t{}',     word),
0x0e: # ASL nn
    ('',   'ASL\t{}',     word),
0x10: # BPL
    ('B',  'BPL\t{}',     am_relative),
0x11: # ORA (n),Y
    ('',   'ORA\t({}),Y', byte),
0x15: # ORA n,X
    ('',   'ORA\t{},X',   byte),
0x16: # ASL n,X
    ('',   'ASL\t{},X',   byte),
0x18: # CLC
    ('',   'CLC'),
0x19: # ORA nn,Y
    ('',   'ORA\t{},Y',   word),
0x1d: # ORA nn,X
    ('',   'ORA\t{},X',   word),
0x1e: # ASL nn,X
    ('',   'ASL\t{},X',   word),
0x20: # JSR nn
    ('B',  'JSR\t{}',     word),
0x21: # AND (n,X)
    ('',   'AND\t({},X)', byte),
0x24: # BIT n
    ('',   'BIT\t{}',     byte),
0x25: # AND n
    ('',   'AND\t{}',     byte),
0x26: # ROL n
    ('',   'ROL\t{}',     byte),
0x28: # PLP
    ('',   'PLP'),
0x29: # AND #n
    ('',   'AND\t#{}',    byte),
0x2a: # ROLA
    ('',   'ROLA'),
0x2c: # BIT nn
    ('',   'BIT\t{}',     word),
0x2d: # AND nn
    ('',   'AND\t{}',     word),
0x2e: # ROL nn
    ('',   'ROL\t{}',     word),
0x30: # BMI
    ('B',  'BMI\t{}',     am_relative),
0x31: # AND (n),Y
    ('',   'AND\t({}),Y', byte),
0x35: # AND n,X
    ('',   'AND\t{},X',   byte),
0x36: # ROL n,X
    ('',   'ROL\t{},X',   byte),
0x38: # SEC
    ('',   'SEC'),
0x39: # AND nn,Y
    ('',   'AND\t{},Y',   word),
0x3d: # AND nn,X
    ('',   'AND\t{},X',   word),
0x3e: # ROL nn,X
    ('',   'ROL\t{},X',   word),
0x40: # RTI
    ('A',  'RTI'),
0x41: # EOR (n,X)
    ('',   'EOR\t({},X)', byte),
0x45: # EOR n
    ('',   'EOR\t{}',     byte),
0x46: # LSR n
    ('',   'LSR\t{}',     byte),
0x48: # PHA
    ('',   'PHA'),
0x49: # EOR #n
    ('',   'EOR\t#{}',    byte),
0x4a: # LSRA
    ('',   'LSRA'),
0x4c: # JMP nn
    ('AB', 'JMP\t{}',     word),
0x4d: # EOR nn
    ('',   'EOR\t{}',     word),
0x4e: # LSR nn
    ('',   'LSR\t{}',     word),
0x50: # BVC
    ('B',  'BVC\t{}',     am_relative),
0x51: # EOR (n),Y
    ('',   'EOR\t({}),Y', byte),
0x55: # EOR n,X
    ('',   'EOR\t{},X',   byte),
0x56: # LSR n,X
    ('',   'LSR\t{},X',   byte),
0x58: # CLI
    ('',   'CLI'),
0x59: # EOR nn,Y
    ('',   'EOR\t{},Y',   word),
0x5d: # EOR nn,X
    ('',   'EOR\t{},X',   word),
0x5e: # LSR nn,X
    ('',   'LSR\t{},X',   word),
0x60: # RTS
    ('A',  'RTS'),
0x61: # ADC (n,X)
    ('',   'ADC\t({},X)', byte),
0x65: # ADC n
    ('',   'ADC\t{}',     byte),
0x66: # ROR n
    ('',   'ROR\t{}',     byte),
0x68: # PLA
    ('',   'PLA'),
0x69: # ADC #n
    ('',   'ADC\t#{}',    byte),
0x6a: # RORA
    ('',   'RORA'),
0x6c: # JMP (nn)
    ('A',  'JMP\t({})',   word),
0x6d: # ADC nn
    ('',   'ADC\t{}',     word),
0x6e: # ROR nn
    ('',   'ROR\t{}',     word),
0x70: # BVS
    ('B',  'BVS\t{}',     am_relative),
0x71: # ADC (n),Y
    ('',   'ADC\t({}),Y', byte),
0x75: # ADC n,X
    ('',   'ADC\t{},X',   byte),
0x76: # ROR n,X
    ('',   'ROR\t{},X',   byte),
0x78: # SEI
    ('',   'SEI'),
0x79: # ADC nn,Y
    ('',   'ADC\t{},Y',   word),
0x7d: # ADC nn,X
    ('',   'ADC\t{},X',   word),
0x7e: # ROR nn,X
    ('',   'ROR\t{},X',   word),
0x81: # STA (n,X)
    ('',   'STA\t({},X)', byte),
0x84: # STY n
    ('',   'STY\t{}',     byte),
0x85: # STA n
    ('',   'STA\t{}',     byte),
0x86: # STX n
    ('',   'STX\t{}',     byte),
0x88: # DEY
    ('',   'DEY'),
0x8a: # TXA
    ('',   'TXA'),
0x8c: # STY nn
    ('',   'STY\t{}',     word),
0x8d: # STA nn
    ('',   'STA\t{}',     word),
0x8e: # STX nn
    ('',   'STX\t{}',     word),
0x90: # BCC
    ('B',  'BCC\t{}',     am_relative),
0x91: # STA (n),Y
    ('',   'STA\t({}),Y', byte),
0x94: # STY n,X
    ('',   'STY\t{},X',   byte),
0x95: # STA n,X
    ('',   'STA\t{},X',   byte),
0x96: # STX n,Y
    ('',   'STX\t{},Y',   byte),
0x98: # TYA
    ('',   'TYA'),
0x99: # STA nn,Y
    ('',   'STA\t{},Y',   word),
0x9a: # TXS
    ('',   'TXS'),
0x9d: # STA nn,X
    ('',   'STA\t{},X',   word),
0xa0: # LDY #n
    ('',   'LDY\t#{}',    byte),
0xa1: # LDA (n,X)
    ('',   'LDA\t({},X)', byte),
0xa2: # LDX #n
    ('',   'LDX\t#{}',    byte),
0xa4: # LDY n
    ('',   'LDY\t{}',     byte),
0xa5: # LDA n
    ('',   'LDA\t{}',     byte),
0xa6: # LDX n
    ('',   'LDX\t{}',     byte),
0xa8: # TAY
    ('',   'TAY'),
0xa9: # LDA #n
    ('',   'LDA\t#{}',    byte),
0xaa: # TAX
    ('',   'TAX'),
0xac: # LDY nn
    ('',   'LDY\t{}',     word),
0xad: # LDA nn
    ('',   'LDA\t{}',     word),
0xae: # LDX nn
    ('',   'LDX\t{}',     word),
0xb0: # BCS
    ('B',  'BCS\t{}',     am_relative),
0xb1: # LDA (n),Y
    ('',   'LDA\t({}),Y', byte),
0xb4: # LDY n,X
    ('',   'LDY\t{},X',   byte),
0xb5: # LDA n,X
    ('',   'LDA\t{},X',   byte),
0xb6: # LDX n,Y
    ('',   'LDX\t{},Y',   byte),
0xb8: # CLV
    ('',   'CLV'),
0xb9: # LDA nn,Y
    ('',   'LDA\t{},Y',   word),
0xba: # TSX
    ('',   'TSX'),
0xbc: # LDY nn,X
    ('',   'LDY\t{},X',   word),
0xbd: # LDA nn,X
    ('',   'LDA\t{},X',   word),
0xbe: # LDX nn,Y
    ('',   'LDX\t{},Y',   word),
0xc0: # CPY #n
    ('',   'CPY\t#{}',    byte),
0xc1: # CMP (n,X)
    ('',   'CMP\t({},X)', byte),
0xc4: # CPY n
    ('',   'CPY\t{}',     byte),
0xc5: # CMP n
    ('',   'CMP\t{}',     byte),
0xc6: # DEC n
    ('',   'DEC\t{}',     byte),
0xc8: # INY
    ('',   'INY'),
0xc9: # CMP #n
    ('',   'CMP\t#{}',    byte),
0xca: # DEX
    ('',   'DEX'),
0xcc: # CPY nn
    ('',   'CPY\t{}',     word),
0xcd: # CMP nn
    ('',   'CMP\t{}',     word),
0xce: # DEC nn
    ('',   'DEC\t{}',     word),
0xd0: # BNE
    ('B',  'BNE\t{}',     am_relative),
0xd1: # CMP (n),Y
    ('',   'CMP\t({}),Y', byte),
0xd5: # CMP n,X
    ('',   'CMP\t{},X',   byte),
0xd6: # DEC n,X
    ('',   'DEC\t{},X',   byte),
0xd8: # CLD
    ('',   'CLD'),
0xd9: # CMP nn,Y
    ('',   'CMP\t{},Y',   word),
0xdd: # CMP nn,X
    ('',   'CMP\t{},X',   word),
0xde: # DEC nn,X
    ('',   'DEC\t{},X',   word),
0xe0: # CPX #n
    ('',   'CPX\t#{}',    byte),
0xe1: # SBC (n,X)
    ('',   'SBC\t({},X)', byte),
0xe4: # CPX n
    ('',   'CPX\t{}',     byte),
0xe5: # SBC n
    ('',   'SBC\t{}',     byte),
0xe6: # INC n
    ('',   'INC\t{}',     byte),
0xe8: # INX
    ('',   'INX'),
0xe9: # SBC #n
    ('',   'SBC\t#{}',    byte),
0xea: # NOP
    ('',   'NOP'),
0xec: # CPX nn
    ('',   'CPX\t{}',     word),
0xed: # SBC nn
    ('',   'SBC\t{}',     word),
0xee: # INC nn
    ('',   'INC\t{}',     word),
0xf0: # BEQ
    ('B',  'BEQ\t{}',     am_relative),
0xf1: # SBC (n),Y
    ('',   'SBC\t({}),Y', byte),
0xf5: # SBC n,X
    ('',   'SBC\t{},X',   byte),
0xf6: # INC n,X
    ('',   'INC\t{},X',   byte),
0xf8: # SED
    ('',   'SED'),
0xf9: # SBC nn,Y
    ('',   'SBC\t{},Y',   word),
0xfd: # SBC nn,X
    ('',   'SBC\t{},X',   word),
0xfe: # INC nn,X
    ('',   'INC\t{},X',   word),
}

def op():
    global flags, table
    opcode = fetch()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[0]
    return t[1].lower().format(*[f() for f in t[2:]])

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
    buffer[start:] = data
    end = start + len(data)
if tablefile:
    for line in tablefile:
        words = line.split(' ')
        if words[0] == 'b':
            base = int(words[1], 16)
            size = int(words[2]) if len(words) > 2 else 1
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
            size = int(words[2]) if len(words) > 2 else 1
            string[base:base + size] = [True] * size
        elif words[0] == 't':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 2] = True
                jumplabel[buffer[base + index * 2] | buffer[base + index * 2 + 1] << 8] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 2] = True
                label[buffer[base + index * 2] | buffer[base + index * 2 + 1] << 8] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 3] = True
                label[buffer[base + index * 3] | buffer[base + index * 3 + 1] << 8] = True

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
    print(f'\t\t\t\torg\t${start:0=4x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMCS6502 disassembler', file=file)
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
        print(f'\tfdb\tL{fetch() | fetch() << 8:0=4x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch() | fetch() << 8:0=4x}', end='', file=file)
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

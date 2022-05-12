#
#   MC6801 disassembler
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
    return f'${fetch():02x}'

def word():
    global jumplabel, label, flags
    operand = fetch() << 8 | fetch()
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
    0x01: ('NOP',      '',   'NOP'),
    0x04: ('LSRD',     '',   'LSRD'),
    0x05: ('ASLD',     '',   'ASLD'),
    0x06: ('TAP',      '',   'TAP'),
    0x07: ('TPA',      '',   'TPA'),
    0x08: ('INX',      '',   'INX'),
    0x09: ('DEX',      '',   'DEX'),
    0x0a: ('CLV',      '',   'CLV'),
    0x0b: ('SEV',      '',   'SEV'),
    0x0c: ('CLC',      '',   'CLC'),
    0x0d: ('SEC',      '',   'SEC'),
    0x0e: ('CLI',      '',   'CLI'),
    0x0f: ('SEI',      '',   'SEI'),
    0x10: ('SBA',      '',   'SBA'),
    0x11: ('CBA',      '',   'CBA'),
    0x16: ('TAB',      '',   'TAB'),
    0x17: ('TBA',      '',   'TBA'),
    0x18: ('XGDX',     '',   'XGDX'), # (HD63701)
    0x19: ('DAA',      '',   'DAA'),
    0x1a: ('SLP',      '',   'SLP'), # (HD63701)
    0x1b: ('ABA',      '',   'ABA'),
    0x20: ('BRA',      'AB', 'BRA\t{}',         am_relative),
    0x21: ('BRN',      'B',  'BRN\t{}',         am_relative),
    0x22: ('BHI',      'B',  'BHI\t{}',         am_relative),
    0x23: ('BLS',      'B',  'BLS\t{}',         am_relative),
    0x24: ('BHS(BCC)', 'B',  'BCC\t{}',         am_relative),
    0x25: ('BLO(BCS)', 'B',  'BCS\t{}',         am_relative),
    0x26: ('BNE',      'B',  'BNE\t{}',         am_relative),
    0x27: ('BEQ',      'B',  'BEQ\t{}',         am_relative),
    0x28: ('BVC',      'B',  'BVC\t{}',         am_relative),
    0x29: ('BVS',      'B',  'BVS\t{}',         am_relative),
    0x2a: ('BPL',      'B',  'BPL\t{}',         am_relative),
    0x2b: ('BMI',      'B',  'BMI\t{}',         am_relative),
    0x2c: ('BGE',      'B',  'BGE\t{}',         am_relative),
    0x2d: ('BLT',      'B',  'BLT\t{}',         am_relative),
    0x2e: ('BGT',      'B',  'BGT\t{}',         am_relative),
    0x2f: ('BLE',      'B',  'BLE\t{}',         am_relative),
    0x30: ('TSX',      '',   'TSX'),
    0x31: ('INS',      '',   'INS'),
    0x32: ('PULA',     '',   'PULA'),
    0x33: ('PULB',     '',   'PULB'),
    0x34: ('DES',      '',   'DES'),
    0x35: ('TXS',      '',   'TXS'),
    0x36: ('PSHA',     '',   'PSHA'),
    0x37: ('PSHB',     '',   'PSHB'),
    0x38: ('PULX',     '',   'PULX'),
    0x39: ('RTS',      'A',  'RTS'),
    0x3a: ('ABX',      '',   'ABX'),
    0x3b: ('RTI',      'A',  'RTI'),
    0x3c: ('PSHX',     '',   'PSHX'),
    0x3d: ('MUL',      '',   'MUL'),
    0x3e: ('WAI',      '',   'WAI'),
    0x3f: ('SWI',      '',   'SWI'),
    0x6e: ('JMP ,X',   'AB', 'JMP\t{},X',       byte),
    0x7e: ('JMP >nn',  'AB', 'JMP\t{}',         word),
    0x8d: ('BSR',      'B',  'BSR\t{}',         am_relative),
    0x9d: ('JSR <n',   'B',  'JSR\t<{}',        byte),
    0xad: ('JSR ,X',   'B',  'JSR\t{},X',       byte),
    0xbd: ('JSR >nn',  'B',  'JSR\t{}',         word),
}

for i, op in {0:'NEG', 3:'COM', 4:'LSR', 6:'ROR', 7:'ASR', 8:'ASL', 9:'ROL', 10:'DEC', 12:'INC', 13:'TST', 15:'CLR'}.items():
    table[0x40 | i] = (f'{op}A', '', f'{op}A')
    table[0x50 | i] = (f'{op}B', '', f'{op}B')
    table[0x60 | i] = (f'{op} ,X', '', f'{op}\t''{},X', byte)
    table[0x70 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)
for i, op in {1:'AIM', 2:'OIM', 5:'EIM', 11:'TIM'}.items(): # (HD63701)
    table[0x60 | i] = (f'{op} ,X', '', f'{op}\t''#{},[{},X]', byte, byte)
    table[0x70 | i] = (f'{op} <n', '', f'{op}\t''#{},<{}', byte, byte)
for i, op in {0:'SUBA', 1:'CMPA', 2:'SBCA', 4:'ANDA', 5:'BITA', 6:'LDAA', 8:'EORA', 9:'ADCA', 0xa:'ORAA', 0xb:'ADDA'}.items():
    table[0x80 | i] = (f'{op} #n', '', f'{op}\t''#{}', byte)
for i, op in {3:'SUBD', 0xc:'CPX', 0xe:'LDS'}.items():
    table[0x80 | i] = (f'{op} #nn', '', f'{op}\t''#{}', word)
for i, op in {0:'SUBA', 1:'CMPA', 2:'SBCA', 3:'SUBD', 4:'ANDA', 5:'BITA', 6:'LDAA', 7:'STAA', 8:'EORA', 9:'ADCA', 0xa:'ORAA', 0xb:'ADDA', 0xc:'CPX', 0xe:'LDS', 0xf:'STS'}.items():
    table[0x90 | i] = (f'{op} <n', '', f'{op}\t''<{}', byte)
    table[0xa0 | i] = (f'{op} ,X', '', f'{op}\t''{},X', byte)
    table[0xb0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)
for i, op in {0:'SUBB', 1:'CMPB', 2:'SBCB', 4:'ANDB', 5:'BITB', 6:'LDAB', 8:'EORB', 9:'ADCB', 0xa:'ORAB', 0xb:'ADDB'}.items():
    table[0xc0 | i] = (f'{op} #n', '', f'{op}\t''#{}', byte)
for i, op in {3:'ADDD', 0xc:'LDD', 0xe:'LDX'}.items():
    table[0xc0 | i] = (f'{op} #nn', '', f'{op}\t''#{}', word)
for i, op in enumerate(('SUBB', 'CMPB', 'SBCB', 'ADDD', 'ANDB', 'BITB', 'LDAB', 'STAB', 'EORB', 'ADCB', 'ORAB', 'ADDB', 'LDD', 'STD', 'LDX', 'STX')):
    table[0xd0 | i] = (f'{op} <n', '', f'{op}\t''<{}', byte)
    table[0xe0 | i] = (f'{op} ,X', '', f'{op}\t''{},X', byte)
    table[0xf0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)

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
    print(f'\t\t\t*\tMC6801 disassembler', file=file)
    print(f'\t\t\t*\tfilename: {args[0]}', file=file)
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t\torg\t${start:04x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMC6801 disassembler', file=file)
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
        print('\t' + s, file=file)
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
        print(f'\tfdb\tL{fetch() << 8 | fetch():04x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch() << 8 | fetch():04x}', end='', file=file)
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

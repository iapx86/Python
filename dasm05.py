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
    operand = fetch() << 8 | fetch()
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
0x00: # BRSET0
    ('B',  'BRSET\t0,<{},{}', byte, am_relative),
0x01: # BRCLR0
    ('B',  'BRCLR\t0,<{},{}', byte, am_relative),
0x02: # BRSET1
    ('B',  'BRSET\t1,<{},{}', byte, am_relative),
0x03: # BRCLR1
    ('B',  'BRCLR\t1,<{},{}', byte, am_relative),
0x04: # BRSET2
    ('B',  'BRSET\t2,<{},{}', byte, am_relative),
0x05: # BRCLR2
    ('B',  'BRCLR\t2,<{},{}', byte, am_relative),
0x06: # BRSET3
    ('B',  'BRSET\t3,<{},{}', byte, am_relative),
0x07: # BRCLR3
    ('B',  'BRCLR\t3,<{},{}', byte, am_relative),
0x08: # BRSET4
    ('B',  'BRSET\t4,<{},{}', byte, am_relative),
0x09: # BRCLR4
    ('B',  'BRCLR\t4,<{},{}', byte, am_relative),
0x0a: # BRSET5
    ('B',  'BRSET\t5,<{},{}', byte, am_relative),
0x0b: # BRCLR5
    ('B',  'BRCLR\t5,<{},{}', byte, am_relative),
0x0c: # BRSET6
    ('B',  'BRSET\t6,<{},{}', byte, am_relative),
0x0d: # BRCLR6
    ('B',  'BRCLR\t6,<{},{}', byte, am_relative),
0x0e: # BRSET7
    ('B',  'BRSET\t7,<{},{}', byte, am_relative),
0x0f: # BRCLR7
    ('B',  'BRCLR\t7,<{},{}', byte, am_relative),
0x10: # BSET0
    ('',   'BSET\t0,<{}',     byte),
0x11: # BCLR0
    ('',   'BCLR\t0,<{}',     byte),
0x12: # BSET1
    ('',   'BSET\t1,<{}',     byte),
0x13: # BCLR1
    ('',   'BCLR\t1,<{}',     byte),
0x14: # BSET2
    ('',   'BSET\t2,<{}',     byte),
0x15: # BCLR2
    ('',   'BCLR\t2,<{}',     byte),
0x16: # BSET3
    ('',   'BSET\t3,<{}',     byte),
0x17: # BCLR3
    ('',   'BCLR\t3,<{}',     byte),
0x18: # BSET4
    ('',   'BSET\t4,<{}',     byte),
0x19: # BCLR4
    ('',   'BCLR\t4,<{}',     byte),
0x1a: # BSET5
    ('',   'BSET\t5,<{}',     byte),
0x1b: # BCLR5
    ('',   'BCLR\t5,<{}',     byte),
0x1c: # BSET6
    ('',   'BSET\t6,<{}',     byte),
0x1d: # BCLR6
    ('',   'BCLR\t6,<{}',     byte),
0x1e: # BSET7
    ('',   'BSET\t7,<{}',     byte),
0x1f: # BCLR7
    ('',   'BCLR\t7,<{}',     byte),
0x20: # BRA
    ('AB', 'BRA\t{}',         am_relative),
0x21: # BRN
    ('B',  'BRN\t{}',         am_relative),
0x22: # BHI
    ('B',  'BHI\t{}',         am_relative),
0x23: # BLS
    ('B',  'BLS\t{}',         am_relative),
0x24: # BCC
    ('B',  'BCC\t{}',         am_relative),
0x25: # BLO(BCS)
    ('B',  'BCS\t{}',         am_relative),
0x26: # BNE
    ('B',  'BNE\t{}',         am_relative),
0x27: # BEQ
    ('B',  'BEQ\t{}',         am_relative),
0x28: # BHCC
    ('B',  'BHCC\t{}',        am_relative),
0x29: # BHCS
    ('B',  'BHCS\t{}',        am_relative),
0x2a: # BPL
    ('B',  'BPL\t{}',         am_relative),
0x2b: # BMI
    ('B',  'BMI\t{}',         am_relative),
0x2c: # BMC
    ('B',  'BMC\t{}',         am_relative),
0x2d: # BMS
    ('B',  'BMS\t{}',         am_relative),
0x2e: # BIL
    ('B',  'BIL\t{}',         am_relative),
0x2f: # BIH
    ('B',  'BIH\t{}',         am_relative),
0x30: # NEG <n
    ('',   'NEG\t<{}',        byte),
0x33: # COM <n
    ('',   'COM\t<{}',        byte),
0x34: # LSR <n
    ('',   'LSR\t<{}',        byte),
0x36: # ROR <n
    ('',   'ROR\t<{}',        byte),
0x37: # ASR <n
    ('',   'ASR\t<{}',        byte),
0x38: # ASL(LSL) <n
    ('',   'ASL\t<{}',        byte),
0x39: # ROL <n
    ('',   'ROL\t<{}',        byte),
0x3a: # DEC <n
    ('',   'DEC\t<{}',        byte),
0x3c: # INC <n
    ('',   'INC\t<{}',        byte),
0x3d: # TST <n
    ('',   'TST\t<{}',        byte),
0x3f: # CLR <n
    ('',   'CLR\t<{}',        byte),
0x40: # NEGA
    ('',   'NEGA'),
0x42: # MUL
    ('',   'MUL'),
0x43: # COMA
    ('',   'COMA'),
0x44: # LSRA
    ('',   'LSRA'),
0x46: # RORA
    ('',   'RORA'),
0x47: # ASRA
    ('',   'ASRA'),
0x48: # ASLA(LSLA)
    ('',   'ASLA'),
0x49: # ROLA
    ('',   'ROLA'),
0x4a: # DECA
    ('',   'DECA'),
0x4c: # INCA
    ('',   'INCA'),
0x4d: # TSTA
    ('',   'TSTA'),
0x4f: # CLRA
    ('',   'CLRA'),
0x50: # NEGX
    ('',   'NEGX'),
0x53: # COMX
    ('',   'COMX'),
0x54: # LSRX
    ('',   'LSRX'),
0x56: # RORX
    ('',   'RORX'),
0x57: # ASRX
    ('',   'ASRX'),
0x58: # ASLX(LSLX)
    ('',   'ASLX'),
0x59: # ROLX
    ('',   'ROLX'),
0x5a: # DECX
    ('',   'DECX'),
0x5c: # INCX
    ('',   'INCX'),
0x5d: # TSTX
    ('',   'TSTX'),
0x5f: # CLRX
    ('',   'CLRX'),
0x60: # NEG n,X
    ('',   'NEG\t{},X',       byte),
0x63: # COM n,X
    ('',   'COM\t{},X',       byte),
0x64: # LSR n,X
    ('',   'LSR\t{},X',       byte),
0x66: # ROR n,X
    ('',   'ROR\t{},X',       byte),
0x67: # ASR n,X
    ('',   'ASR\t{},X',       byte),
0x68: # ASL(LSL) n,X
    ('',   'ASL\t{},X',       byte),
0x69: # ROL n,X
    ('',   'ROL\t{},X',       byte),
0x6a: # DEC n,X
    ('',   'DEC\t{},X',       byte),
0x6c: # INC n,X
    ('',   'INC\t{},X',       byte),
0x6d: # TST n,X
    ('',   'TST\t{},X',       byte),
0x6f: # CLR n,X
    ('',   'CLR\t{},X',       byte),
0x70: # NEG ,X
    ('',   'NEG\t,X'),
0x73: # COM ,X
    ('',   'COM\t,X'),
0x74: # LSR ,X
    ('',   'LSR\t,X'),
0x76: # ROR ,X
    ('',   'ROR\t,X'),
0x77: # ASR ,X
    ('',   'ASR\t,X'),
0x78: # ASL(LSL) ,X
    ('',   'ASL\t,X'),
0x79: # ROL ,X
    ('',   'ROL\t,X'),
0x7a: # DEC ,X
    ('',   'DEC\t,X'),
0x7c: # INC ,X
    ('',   'INC\t,X'),
0x7d: # TST ,X
    ('',   'TST\t,X'),
0x7f: # CLR ,X
    ('',   'CLR\t,X'),
0x80: # RTI
    ('A',  'RTI'),
0x81: # RTS
    ('A',  'RTS'),
0x83: # SWI
    ('',   'SWI'),
0x8e: # STOP
    ('',   'STOP'),
0x8f: # WAIT
    ('',   'WAIT'),
0x97: # TAX
    ('',   'TAX'),
0x98: # CLC
    ('',   'CLC'),
0x99: # SEC
    ('',   'SEC'),
0x9a: # CLI
    ('',   'CLI'),
0x9b: # SEI
    ('',   'SEI'),
0x9c: # RSP
    ('',   'RSP'),
0x9d: # NOP
    ('',   'NOP'),
0x9f: # TXA
    ('',   'TXA'),
0xa0: # SUB #n
    ('',   'SUB\t#{}',        byte),
0xa1: # CMP #n
    ('',   'CMP\t#{}',        byte),
0xa2: # SBC #n
    ('',   'SBC\t#{}',        byte),
0xa3: # CPX #n
    ('',   'CPX\t#{}',        byte),
0xa4: # AND #n
    ('',   'AND\t#{}',        byte),
0xa5: # BIT #n
    ('',   'BIT\t#{}',        byte),
0xa6: # LDA #n
    ('',   'LDA\t#{}',        byte),
0xa8: # EOR #n
    ('',   'EOR\t#{}',        byte),
0xa9: # ADC #n
    ('',   'ADC\t#{}',        byte),
0xaa: # ORA #n
    ('',   'ORA\t#{}',        byte),
0xab: # ADD #n
    ('',   'ADD\t#{}',        byte),
0xad: # BSR
    ('B',  'BSR\t{}',         am_relative),
0xae: # LDX #n
    ('',   'LDX\t#{}',        byte),
0xb0: # SUB <n
    ('',   'SUB\t<{}',        byte),
0xb1: # CMP <n
    ('',   'CMP\t<{}',        byte),
0xb2: # SBC <n
    ('',   'SBC\t<{}',        byte),
0xb3: # CPX <n
    ('',   'CPX\t<{}',        byte),
0xb4: # AND <n
    ('',   'AND\t<{}',        byte),
0xb5: # BIT <n
    ('',   'BIT\t<{}',        byte),
0xb6: # LDA <n
    ('',   'LDA\t<{}',        byte),
0xb7: # STA <n
    ('',   'STA\t<{}',        byte),
0xb8: # EOR <n
    ('',   'EOR\t<{}',        byte),
0xb9: # ADC <n
    ('',   'ADC\t<{}',        byte),
0xba: # ORA <n
    ('',   'ORA\t<{}',        byte),
0xbb: # ADD <n
    ('',   'ADD\t<{}',        byte),
0xbc: # JMP <n
    ('A', 'JMP\t<{}',         byte),
0xbd: # JSR <n
    ('',  'JSR\t<{}',         byte),
0xbe: # LDX <n
    ('',   'LDX\t<{}',        byte),
0xbf: # STX <n
    ('',   'STX\t<{}',        byte),
0xc0: # SUB >nn
    ('',   'SUB\t{}',         word),
0xc1: # CMP >nn
    ('',   'CMP\t{}',         word),
0xc2: # SBC >nn
    ('',   'SBC\t{}',         word),
0xc3: # CPX >nn
    ('',   'CPX\t{}',         word),
0xc4: # AND >nn
    ('',   'AND\t{}',         word),
0xc5: # BIT >nn
    ('',   'BIT\t{}',         word),
0xc6: # LDA >nn
    ('',   'LDA\t{}',         word),
0xc7: # STA >nn
    ('',   'STA\t{}',         word),
0xc8: # EOR >nn
    ('',   'EOR\t{}',         word),
0xc9: # ADC >nn
    ('',   'ADC\t{}',         word),
0xca: # ORA >nn
    ('',   'ORA\t{}',         word),
0xcb: # ADD >nn
    ('',   'ADD\t{}',         word),
0xcc: # JMP >nn
    ('AB', 'JMP\t{}',         word),
0xcd: # JSR >nn
    ('B',  'JSR\t{}',         word),
0xce: # LDX >nn
    ('',   'LDX\t{}',         word),
0xcf: # STX >nn
    ('',   'STX\t{}',         word),
0xd0: # SUB nn,X
    ('',   'SUB\t{},X',       word),
0xd1: # CMP nn,X
    ('',   'CMP\t{},X',       word),
0xd2: # SBC nn,X
    ('',   'SBC\t{},X',       word),
0xd3: # CPX nn,X
    ('',   'CPX\t{},X',       word),
0xd4: # AND nn,X
    ('',   'AND\t{},X',       word),
0xd5: # BIT nn,X
    ('',   'BIT\t{},X',       word),
0xd6: # LDA nn,X
    ('',   'LDA\t{},X',       word),
0xd7: # STA nn,X
    ('',   'STA\t{},X',       word),
0xd8: # EOR nn,X
    ('',   'EOR\t{},X',       word),
0xd9: # ADC nn,X
    ('',   'ADC\t{},X',       word),
0xda: # ORA nn,X
    ('',   'ORA\t{},X',       word),
0xdb: # ADD nn,X
    ('',   'ADD\t{},X',       word),
0xdc: # JMP nn,X
    ('AB', 'JMP\t{},X',       word),
0xdd: # JSR nn,X
    ('B',  'JSR\t{},X',       word),
0xde: # LDX nn,X
    ('',   'LDX\t{},X',       word),
0xdf: # STX nn,X
    ('',   'STX\t{},X',       word),
0xe0: # SUB n,X
    ('',   'SUB\t{},X',       byte),
0xe1: # CMP n,X
    ('',   'CMP\t{},X',       byte),
0xe2: # SBC n,X
    ('',   'SBC\t{},X',       byte),
0xe3: # CPX n,X
    ('',   'CPX\t{},X',       byte),
0xe4: # AND n,X
    ('',   'AND\t{},X',       byte),
0xe5: # BIT n,X
    ('',   'BIT\t{},X',       byte),
0xe6: # LDA n,X
    ('',   'LDA\t{},X',       byte),
0xe7: # STA n,X
    ('',   'STA\t{},X',       byte),
0xe8: # EOR n,X
    ('',   'EOR\t{},X',       byte),
0xe9: # ADC n,X
    ('',   'ADC\t{},X',       byte),
0xea: # ORA n,X
    ('',   'ORA\t{},X',       byte),
0xeb: # ADD n,X
    ('',   'ADD\t{},X',       byte),
0xec: # JMP n,X
    ('A',  'JMP\t{},X',       byte),
0xed: # JSR n,X
    ('',   'JSR\t{},X',       byte),
0xee: # LDX n,X
    ('',   'LDX\t{},X',       byte),
0xef: # STX n,X
    ('',   'STX\t{},X',       byte),
0xf0: # SUB ,X
    ('',   'SUB\t,X'),
0xf1: # CMP ,X
    ('',   'CMP\t,X'),
0xf2: # SBC ,X
    ('',   'SBC\t,X'),
0xf3: # CPX ,X
    ('',   'CPX\t,X'),
0xf4: # AND ,X
    ('',   'AND\t,X'),
0xf5: # BIT ,X
    ('',   'BIT\t,X'),
0xf6: # LDA ,X
    ('',   'LDA\t,X'),
0xf7: # STA ,X
    ('',   'STA\t,X'),
0xf8: # EOR ,X
    ('',   'EOR\t,X'),
0xf9: # ADC ,X
    ('',   'ADC\t,X'),
0xfa: # ORA ,X
    ('',   'ORA\t,X'),
0xfb: # ADD ,X
    ('',   'ADD\t,X'),
0xfc: # JMP ,X
    ('A',  'JMP\t,X'),
0xfd: # JSR ,X
    ('',   'JSR\t,X'),
0xfe: # LDX ,X
    ('',   'LDX\t,X'),
0xff: # STX ,X
    ('',   'STX\t,X'),
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
                jumplabel[buffer[base + index * 2] << 8 | buffer[base + index * 2 + 1]] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 2] = True
                label[buffer[base + index * 2] << 8 | buffer[base + index * 2 + 1]] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 3] = True
                label[buffer[base + index * 3] << 8 | buffer[base + index * 3 + 1]] = True

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

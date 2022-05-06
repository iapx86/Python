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
0x01: # NOP
    ('',   'NOP'),
0x04: # LSRD
    ('',   'LSRD'),
0x05: # ASLD
    ('',   'ASLD'),
0x06: # TAP
    ('',   'TAP'),
0x07: # TPA
    ('',   'TPA'),
0x08: # INX
    ('',   'INX'),
0x09: # DEX
    ('',   'DEX'),
0x0a: # CLV
    ('',   'CLV'),
0x0b: # SEV
    ('',   'SEV'),
0x0c: # CLC
    ('',   'CLC'),
0x0d: # SEC
    ('',   'SEC'),
0x0e: # CLI
    ('',   'CLI'),
0x0f: # SEI
    ('',   'SEI'),
0x10: # SBA
    ('',   'SBA'),
0x11: # CBA
    ('',   'CBA'),
0x16: # TAB
    ('',   'TAB'),
0x17: # TBA
    ('',   'TBA'),
0x18: # XGDX (HD63701)
    ('',   'XGDX'),
0x19: # DAA
    ('',   'DAA'),
0x1a: # SLP (HD63701)
    ('',   'SLP'),
0x1b: # ABA
    ('',   'ABA'),
0x20: # BRA
    ('AB', 'BRA\t{}',         am_relative),
0x21: # BRN
    ('B',  'BRN\t{}',         am_relative),
0x22: # BHI
    ('B',  'BHI\t{}',         am_relative),
0x23: # BLS
    ('B',  'BLS\t{}',         am_relative),
0x24: # BHS(BCC)
    ('B',  'BCC\t{}',         am_relative),
0x25: # BLO(BCS)
    ('B',  'BCS\t{}',         am_relative),
0x26: # BNE
    ('B',  'BNE\t{}',         am_relative),
0x27: # BEQ
    ('B',  'BEQ\t{}',         am_relative),
0x28: # BVC
    ('B',  'BVC\t{}',         am_relative),
0x29: # BVS
    ('B',  'BVS\t{}',         am_relative),
0x2a: # BPL
    ('B',  'BPL\t{}',         am_relative),
0x2b: # BMI
    ('B',  'BMI\t{}',         am_relative),
0x2c: # BGE
    ('B',  'BGE\t{}',         am_relative),
0x2d: # BLT
    ('B',  'BLT\t{}',         am_relative),
0x2e: # BGT
    ('B',  'BGT\t{}',         am_relative),
0x2f: # BLE
    ('B',  'BLE\t{}',         am_relative),
0x30: # TSX
    ('',   'TSX'),
0x31: # INS
    ('',   'INS'),
0x32: # PULA
    ('',   'PULA'),
0x33: # PULB
    ('',   'PULB'),
0x34: # DES
    ('',   'DES'),
0x35: # TXS
    ('',   'TXS'),
0x36: # PSHA
    ('',   'PSHA'),
0x37: # PSHB
    ('',   'PSHB'),
0x38: # PULX
    ('',   'PULX'),
0x39: # RTS
    ('A',  'RTS'),
0x3a: # ABX
    ('',   'ABX'),
0x3b: # RTI
    ('A',  'RTI'),
0x3c: # PSHX
    ('',   'PSHX'),
0x3d: # MUL
    ('',   'MUL'),
0x3e: # WAI
    ('',   'WAI'),
0x3f: # SWI
    ('',   'SWI'),
0x40: # NEGA
    ('',   'NEGA'),
0x43: # COMA
    ('',   'COMA'),
0x44: # LSRA
    ('',   'LSRA'),
0x46: # RORA
    ('',   'RORA'),
0x47: # ASRA
    ('',   'ASRA'),
0x48: # ASLA
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
0x50: # NEGB
    ('',   'NEGB'),
0x53: # COMB
    ('',   'COMB'),
0x54: # LSRB
    ('',   'LSRB'),
0x56: # RORB
    ('',   'RORB'),
0x57: # ASRB
    ('',   'ASRB'),
0x58: # ASLB
    ('',   'ASLB'),
0x59: # ROLB
    ('',   'ROLB'),
0x5a: # DECB
    ('',   'DECB'),
0x5c: # INCB
    ('',   'INCB'),
0x5d: # TSTB
    ('',   'TSTB'),
0x5f: # CLRB
    ('',   'CLRB'),
0x60: # NEG ,X
    ('',   'NEG\t{},X',       byte),
0x61: # AIM ,X (HD63701)
    ('',   'AIM\t#{},[{},X]', byte, byte),
0x62: # OIM ,X (HD63701)
    ('',   'OIM\t#{},[{},X]', byte, byte),
0x63: # COM ,X
    ('',   'COM\t{},X',       byte),
0x64: # LSR ,X
    ('',   'LSR\t{},X',       byte),
0x65: # EIM ,X (HD63701)
    ('',   'EIM\t#{},[{},X]', byte, byte),
0x66: # ROR ,X
    ('',   'ROR\t{},X',       byte),
0x67: # ASR ,X
    ('',   'ASR\t{},X',       byte),
0x68: # LSL ,X
    ('',   'LSL\t{},X',       byte),
0x69: # ROL ,X
    ('',   'ROL\t{},X',       byte),
0x6a: # DEC ,X
    ('',   'DEC\t{},X',       byte),
0x6b: # TIM ,X (HD63701)
    ('',   'TIM\t#{},[{},X]', byte, byte),
0x6c: # INC ,X
    ('',   'INC\t{},X',       byte),
0x6d: # TST ,X
    ('',   'TST\t{},X',       byte),
0x6e: # JMP ,X
    ('A',  'JMP\t{},X',       byte),
0x6f: # CLR ,X
    ('',   'CLR\t{},X',       byte),
0x70: # NEG >nn
    ('',   'NEG\t{}',         word),
0x71: # AIM <n (HD63701)
    ('',   'AIM\t#{},<{}',    byte, byte),
0x72: # OIM <n (HD63701)
    ('',   'OIM\t#{},<{}',    byte, byte),
0x73: # COM >nn
    ('',   'COM\t{}',         word),
0x74: # LSR >nn
    ('',   'LSR\t{}',         word),
0x75: # EIM <n (HD63701)
    ('',   'EIM\t#{},<{}',    byte, byte),
0x76: # ROR >nn
    ('',   'ROR\t{}',         word),
0x77: # ASR >nn
    ('',   'ASR\t{}',         word),
0x78: # LSL >nn
    ('',   'LSL\t{}',         word),
0x79: # ROL >nn
    ('',   'ROL\t{}',         word),
0x7a: # DEC >nn
    ('',   'DEC\t{}',         word),
0x7b: # TIM <n (HD63701)
    ('',   'TIM\t#{},<{}',    byte, byte),
0x7c: # INC >nn
    ('',   'INC\t{}',         word),
0x7d: # TST >nn
    ('',   'TST\t{}',         word),
0x7e: # JMP >nn
    ('AB', 'JMP\t{}',         word),
0x7f: # CLR >nn
    ('',   'CLR\t{}',         word),
0x80: # SUBA #n
    ('',   'SUBA\t#{}',       byte),
0x81: # CMPA #n
    ('',   'CMPA\t#{}',       byte),
0x82: # SBCA #n
    ('',   'SBCA\t#{}',       byte),
0x83: # SUBD #nn
    ('',   'SUBD\t#{}',       word),
0x84: # ANDA #n
    ('',   'ANDA\t#{}',       byte),
0x85: # BITA #n
    ('',   'BITA\t#{}',       byte),
0x86: # LDAA #n
    ('',   'LDAA\t#{}',       byte),
0x88: # EORA #n
    ('',   'EORA\t#{}',       byte),
0x89: # ADCA #n
    ('',   'ADCA\t#{}',       byte),
0x8a: # ORAA #n
    ('',   'ORAA\t#{}',       byte),
0x8b: # ADDA #n
    ('',   'ADDA\t#{}',       byte),
0x8c: # CPX #nn
    ('',   'CPX\t#{}',        word),
0x8d: # BSR
    ('B',  'BSR\t{}',         am_relative),
0x8e: # LDS #nn
    ('',   'LDS\t#{}',        word),
0x90: # SUBA <n
    ('',   'SUBA\t<{}',       byte),
0x91: # CMPA <n
    ('',   'CMPA\t<{}',       byte),
0x92: # SBCA <n
    ('',   'SBCA\t<{}',       byte),
0x93: # SUBD <n
    ('',   'SUBD\t<{}',       byte),
0x94: # ANDA <n
    ('',   'ANDA\t<{}',       byte),
0x95: # BITA <n
    ('',   'BITA\t<{}',       byte),
0x96: # LDAA <n
    ('',   'LDAA\t<{}',       byte),
0x97: # STAA <n
    ('',   'STAA\t<{}',       byte),
0x98: # EORA <n
    ('',   'EORA\t<{}',       byte),
0x99: # ADCA <n
    ('',   'ADCA\t<{}',       byte),
0x9a: # ORAA <n
    ('',   'ORAA\t<{}',       byte),
0x9b: # ADDA <n
    ('',   'ADDA\t<{}',       byte),
0x9c: # CPX <n
    ('',   'CPX\t<{}',        byte),
0x9d: # JSR <n
    ('',   'JSR\t<{}',        byte),
0x9e: # LDS <n
    ('',   'LDS\t<{}',        byte),
0x9f: # STS <n
    ('',   'STS\t<{}',        byte),
0xa0: # SUBA ,X
    ('',   'SUBA\t{},X',      byte),
0xa1: # CMPA ,X
    ('',   'CMPA\t{},X',      byte),
0xa2: # SBCA ,X
    ('',   'SBCA\t{},X',      byte),
0xa3: # SUBD ,X
    ('',   'SUBD\t{},X',      byte),
0xa4: # ANDA ,X
    ('',   'ANDA\t{},X',      byte),
0xa5: # BITA ,X
    ('',   'BITA\t{},X',      byte),
0xa6: # LDAA ,X
    ('',   'LDAA\t{},X',      byte),
0xa7: # STAA ,X
    ('',   'STAA\t{},X',      byte),
0xa8: # EORA ,X
    ('',   'EORA\t{},X',      byte),
0xa9: # ADCA ,X
    ('',   'ADCA\t{},X',      byte),
0xaa: # ORAA ,X
    ('',   'ORAA\t{},X',      byte),
0xab: # ADDA ,X
    ('',   'ADDA\t{},X',      byte),
0xac: # CPX ,X
    ('',   'CPX\t{},X',       byte),
0xad: # JSR ,X
    ('',   'JSR\t{},X',       byte),
0xae: # LDS ,X
    ('',   'LDS\t{},X',       byte),
0xaf: # STS ,X
    ('',   'STS\t{},X',       byte),
0xb0: # SUBA >nn
    ('',   'SUBA\t{}',        word),
0xb1: # CMPA >nn
    ('',   'CMPA\t{}',        word),
0xb2: # SBCA >nn
    ('',   'SBCA\t{}',        word),
0xb3: # SUBD >nn
    ('',   'SUBD\t{}',        word),
0xb4: # ANDA >nn
    ('',   'ANDA\t{}',        word),
0xb5: # BITA >nn
    ('',   'BITA\t{}',        word),
0xb6: # LDAA >nn
    ('',   'LDAA\t{}',        word),
0xb7: # STAA >nn
    ('',   'STAA\t{}',        word),
0xb8: # EORA >nn
    ('',   'EORA\t{}',        word),
0xb9: # ADCA >nn
    ('',   'ADCA\t{}',        word),
0xba: # ORAA >nn
    ('',   'ORAA\t{}',        word),
0xbb: # ADDA >nn
    ('',   'ADDA\t{}',        word),
0xbc: # CPX >nn
    ('',   'CPX\t{}',         word),
0xbd: # JSR >nn
    ('B',  'JSR\t{}',         word),
0xbe: # LDS >nn
    ('',   'LDS\t{}',         word),
0xbf: # STS >nn
    ('',   'STS\t{}',         word),
0xc0: # SUBB #n
    ('',   'SUBB\t#{}',       byte),
0xc1: # CMPB #n
    ('',   'CMPB\t#{}',       byte),
0xc2: # SBCB #n
    ('',   'SBCB\t#{}',       byte),
0xc3: # ADDD #nn
    ('',   'ADDD\t#{}',       word),
0xc4: # ANDB #n
    ('',   'ANDB\t#{}',       byte),
0xc5: # BITB #n
    ('',   'BITB\t#{}',       byte),
0xc6: # LDAB #n
    ('',   'LDAB\t#{}',       byte),
0xc8: # EORB #n
    ('',   'EORB\t#{}',       byte),
0xc9: # ADCB #n
    ('',   'ADCB\t#{}',       byte),
0xca: # ORAB #n
    ('',   'ORAB\t#{}',       byte),
0xcb: # ADDB #n
    ('',   'ADDB\t#{}',       byte),
0xcc: # LDD #nn
    ('',   'LDD\t#{}',        word),
0xce: # LDX #nn
    ('',   'LDX\t#{}',        word),
0xd0: # SUBB <n
    ('',   'SUBB\t<{}',       byte),
0xd1: # CMPB <n
    ('',   'CMPB\t<{}',       byte),
0xd2: # SBCB <n
    ('',   'SBCB\t<{}',       byte),
0xd3: # ADDD <n
    ('',   'ADDD\t<{}',       byte),
0xd4: # ANDB <n
    ('',   'ANDB\t<{}',       byte),
0xd5: # BITB <n
    ('',   'BITB\t<{}',       byte),
0xd6: # LDAB <n
    ('',   'LDAB\t<{}',       byte),
0xd7: # STAB <n
    ('',   'STAB\t<{}',       byte),
0xd8: # EORB <n
    ('',   'EORB\t<{}',       byte),
0xd9: # ADCB <n
    ('',   'ADCB\t<{}',       byte),
0xda: # ORAB <n
    ('',   'ORAB\t<{}',       byte),
0xdb: # ADDB <n
    ('',   'ADDB\t<{}',       byte),
0xdc: # LDD <n
    ('',   'LDD\t<{}',        byte),
0xdd: # STD <n
    ('',   'STD\t<{}',        byte),
0xde: # LDX <n
    ('',   'LDX\t<{}',        byte),
0xdf: # STX <n
    ('',   'STX\t<{}',        byte),
0xe0: # SUBB ,X
    ('',   'SUBB\t{},X',      byte),
0xe1: # CMPB ,X
    ('',   'CMPB\t{},X',      byte),
0xe2: # SBCB ,X
    ('',   'SBCB\t{},X',      byte),
0xe3: # ADDD ,X
    ('',   'ADDD\t{},X',      byte),
0xe4: # ANDB ,X
    ('',   'ANDB\t{},X',      byte),
0xe5: # BITB ,X
    ('',   'BITB\t{},X',      byte),
0xe6: # LDAB ,X
    ('',   'LDAB\t{},X',      byte),
0xe7: # STAB ,X
    ('',   'STAB\t{},X',      byte),
0xe8: # EORB ,X
    ('',   'EORB\t{},X',      byte),
0xe9: # ADCB ,X
    ('',   'ADCB\t{},X',      byte),
0xea: # ORAB ,X
    ('',   'ORAB\t{},X',      byte),
0xeb: # ADDB ,X
    ('',   'ADDB\t{},X',      byte),
0xec: # LDD ,X
    ('',   'LDD\t{},X',       byte),
0xed: # STD ,X
    ('',   'STD\t{},X',       byte),
0xee: # LDX ,X
    ('',   'LDX\t{},X',       byte),
0xef: # STX ,X
    ('',   'STX\t{},X',       byte),
0xf0: # SUBB >nn
    ('',   'SUBB\t{}',        word),
0xf1: # CMPB >nn
    ('',   'CMPB\t{}',        word),
0xf2: # SBCB >nn
    ('',   'SBCB\t{}',        word),
0xf3: # ADDD >nn
    ('',   'ADDD\t{}',        word),
0xf4: # ANDB >nn
    ('',   'ANDB\t{}',        word),
0xf5: # BITB >nn
    ('',   'BITB\t{}',        word),
0xf6: # LDAB >nn
    ('',   'LDAB\t{}',        word),
0xf7: # STAB >nn
    ('',   'STAB\t{}',        word),
0xf8: # EORB >nn
    ('',   'EORB\t{}',        word),
0xf9: # ADCB >nn
    ('',   'ADCB\t{}',        word),
0xfa: # ORAB >nn
    ('',   'ORAB\t{}',        word),
0xfb: # ADDB >nn
    ('',   'ADDB\t{}',        word),
0xfc: # LDD >nn
    ('',   'LDD\t{}',         word),
0xfd: # STD >nn
    ('',   'STD\t{}',         word),
0xfe: # LDX >nn
    ('',   'LDX\t{}',         word),
0xff: # STX >nn
    ('',   'STX\t{}',         word),
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
    print(f'\t\t\t*\tMC6801 disassembler', file=file)
    print(f'\t\t\t*\tfilename: {args[0]}', file=file)
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t\torg\t${start:0=4x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMC6801 disassembler', file=file)
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

#
#   MC6809 disassembler
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
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def am_lrelative():
    global jumplabel, label, location, flags
    operand = (fetch() << 8 | fetch()) + location & 0xffff
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def am_index():
    post = fetch()
    if post & 0x80 and post & 0x1f in (0x07, 0x0a, 0x0e, 0x0f, 0x10, 0x12, 0x17, 0x1a, 0x1e):
        return ''
    pl = post & 15
    if not post & 0x80:
        d = post & 15 | -(post & 16)
        offset = ('-' if d < 0 else '') + f'${abs(d):0=2x}'
    elif pl == 5:
        offset = 'b'
    elif pl == 6:
        offset = 'a'
    elif pl == 8:
        d = (lambda x : x & 0x7f | -(x & 0x80))(fetch())
        offset = ('-' if d < 0 else '') + f'${abs(d):0=2x}'
    elif pl == 9 or pl == 15:
        offset = word()
    elif pl == 11:
        offset = 'd'
    elif pl == 12:
        offset = am_relative()
    elif pl == 13:
        offset = am_lrelative()
    else:
        offset = ''
    dec = ('-', '--')[post & 1] if (post & 0x8e) == 0x82 else ''
    reg = ('x', 'y', 'u', 's')[post >> 5 & 3] if (post & 0x8e) != 0x8c else 'pc'
    inc = ('+', '++')[post & 1] if (post & 0x8e) == 0x80 else ''
    return f'{offset},{dec}{reg}{inc}' if not post & 0x80 or not post & 0x10 else f'[{offset},{dec}{reg}{inc}]' if pl != 0x0f else f'[{offset}]'

def exg_tfr():
    post = fetch()
    regs = {0:'d', 1:'x', 2:'y', 3:'u', 4:'s', 5:'pc', 8:'a', 9:'b', 0xa:'cc', 0xb:'dp'}
    return f'{regs[post >> 4]},{regs[post & 15]}' if post >> 4 in regs and post & 15 in regs else ''

def psh_pul():
    global buffer, location
    post = fetch()
    regs = ('cc', 'a', 'b', 'dp', 'x', 'y', 's' if buffer[location - 2] & 2 else 'u', 'pc')
    return ','.join([reg for i, reg in enumerate(regs) if post & 1 << i])

table_11 = {
    0x3f: ('SWI3',     '',   'SWI3'),
}

for i, op in {3:'CMPU', 0xc:'CMPS'}.items():
    table_11[0x80 | i] = (f'{op} #nn', '', f'{op}\t''#{}', word)
    table_11[0x90 | i] = (f'{op} <n', '', f'{op}\t''<{}', byte)
    table_11[0xa0 | i] = (f'{op} ,r', '', f'{op}\t''{}', am_index)
    table_11[0xb0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)

def op_11():
    global flags, table_11
    opcode = fetch()
    if opcode not in table_11:
        return ''
    t = table_11[opcode]
    flags = t[1]
    operands = [f() for f in t[3:]]
    return t[2].lower().format(*operands) if '' not in operands else ''

table_10 = {
    0x21: ('LBRN',       'B',  'LBRN\t{}',   am_lrelative),
    0x22: ('LBHI',       'B',  'LBHI\t{}',   am_lrelative),
    0x23: ('LBLS',       'B',  'LBLS\t{}',   am_lrelative),
    0x24: ('LBHS(LBCC)', 'B',  'LBCC\t{}',   am_lrelative),
    0x25: ('LBLO(LBCS)', 'B',  'LBCS\t{}',   am_lrelative),
    0x26: ('LBNE',       'B',  'LBNE\t{}',   am_lrelative),
    0x27: ('LBEQ',       'B',  'LBEQ\t{}',   am_lrelative),
    0x28: ('LBVC',       'B',  'LBVC\t{}',   am_lrelative),
    0x29: ('LBVS',       'B',  'LBVS\t{}',   am_lrelative),
    0x2a: ('LBPL',       'B',  'LBPL\t{}',   am_lrelative),
    0x2b: ('LBMI',       'B',  'LBMI\t{}',   am_lrelative),
    0x2c: ('LBGE',       'B',  'LBGE\t{}',   am_lrelative),
    0x2d: ('LBLT',       'B',  'LBLT\t{}',   am_lrelative),
    0x2e: ('LBGT',       'B',  'LBGT\t{}',   am_lrelative),
    0x2f: ('LBLE',       'B',  'LBLE\t{}',   am_lrelative),
    0x3f: ('SWI2',       '',   'SWI2'),
    0xce: ('LDS #nn',    '',   'LDS\t#{}',   word),
}

for i, op in {3:'CMPD', 0xc:'CMPY', 0xe:'LDY'}.items():
    table_10[0x80 | i] = (f'{op} #nn', '', f'{op}\t''#{}', word)
for i, op in {3:'CMPD', 0xc:'CMPY', 0xe:'LDY', 0xf:'STY'}.items():
    table_10[0x90 | i] = (f'{op} <n', '', f'{op}\t''<{}', byte)
    table_10[0xa0 | i] = (f'{op} ,r', '', f'{op}\t''{}', am_index)
    table_10[0xb0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)
for i, op in {0xe:'LDS', 0xf:'STS'}.items():
    table_10[0xd0 | i] = (f'{op} <n', '', f'{op}\t''<{}', byte)
    table_10[0xe0 | i] = (f'{op} ,r', '', f'{op}\t''{}', am_index)
    table_10[0xf0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)

def op_10():
    global flags, table_10
    opcode = fetch()
    if opcode not in table_10:
        return ''
    t = table_10[opcode]
    flags = t[1]
    operands = [f() for f in t[3:]]
    return t[2].lower().format(*operands) if '' not in operands else ''

table = {
    0x0e: ('JMP <n',   'A',  'JMP\t{}',    byte),
    0x10: ('',         '',   '{}',         op_10),
    0x11: ('',         '',   '{}',         op_11),
    0x12: ('NOP',      '',   'NOP'),
    0x13: ('SYNC',     '',   'SYNC'),
    0x16: ('LBRA',     'AB', 'LBRA\t{}',   am_lrelative),
    0x17: ('LBSR',     'B',  'LBSR\t{}',   am_lrelative),
    0x19: ('DAA',      '',   'DAA'),
    0x1a: ('ORCC',     '',   'ORCC\t#{}',  byte),
    0x1c: ('ANDCC',    '',   'ANDCC\t#{}', byte),
    0x1d: ('SEX',      '',   'SEX'),
    0x1e: ('EXG',      '',   'EXG\t{}',    exg_tfr),
    0x1f: ('TFR',      '',   'TFR\t{}',    exg_tfr),
    0x20: ('BRA',      'AB', 'BRA\t{}',    am_relative),
    0x21: ('BRN',      'B',  'BRN\t{}',    am_relative),
    0x22: ('BHI',      'B',  'BHI\t{}',    am_relative),
    0x23: ('BLS',      'B',  'BLS\t{}',    am_relative),
    0x24: ('BHS(BCC)', 'B',  'BCC\t{}',    am_relative),
    0x25: ('BLO(BCS)', 'B',  'BCS\t{}',    am_relative),
    0x26: ('BNE',      'B',  'BNE\t{}',    am_relative),
    0x27: ('BEQ',      'B',  'BEQ\t{}',    am_relative),
    0x28: ('BVC',      'B',  'BVC\t{}',    am_relative),
    0x29: ('BVS',      'B',  'BVS\t{}',    am_relative),
    0x2a: ('BPL',      'B',  'BPL\t{}',    am_relative),
    0x2b: ('BMI',      'B',  'BMI\t{}',    am_relative),
    0x2c: ('BGE',      'B',  'BGE\t{}',    am_relative),
    0x2d: ('BLT',      'B',  'BLT\t{}',    am_relative),
    0x2e: ('BGT',      'B',  'BGT\t{}',    am_relative),
    0x2f: ('BLE',      'B',  'BLE\t{}',    am_relative),
    0x30: ('LEAX',     '',   'LEAX\t{}',   am_index),
    0x31: ('LEAY',     '',   'LEAY\t{}',   am_index),
    0x32: ('LEAS',     '',   'LEAS\t{}',   am_index),
    0x33: ('LEAU',     '',   'LEAU\t{}',   am_index),
    0x34: ('PSHS',     '',   'PSHS\t{}',   psh_pul),
    0x35: ('PULS',     '',   'PULS\t{}',   psh_pul),
    0x36: ('PSHU',     '',   'PSHU\t{}',   psh_pul),
    0x37: ('PULU',     '',   'PULU\t{}',   psh_pul),
    0x39: ('RTS',      'A',  'RTS'),
    0x3a: ('ABX',      '',   'ABX'),
    0x3b: ('RTI',      'A',  'RTI'),
    0x3c: ('CWAI',     '',   'CWAI\t#{}',  byte),
    0x3d: ('MUL',      '',   'MUL'),
    0x3f: ('SWI',      '',   'SWI'),
    0x6e: ('JMP ,r',   'A',  'JMP\t{}',    am_index),
    0x7e: ('JMP >nn',  'AB', 'JMP\t{}',    word),
    0x8d: ('BSR',      'B',  'BSR\t{}',    am_relative),
    0x9d: ('JSR <n',   'B',   'JSR\t<{}',  byte),
    0xad: ('JSR ,r',   'B',   'JSR\t{}',   am_index),
    0xbd: ('JSR >nn',  'B',  'JSR\t{}',    word),
}

for i, op in {0:'NEG', 3:'COM', 4:'LSR', 6:'ROR', 7:'ASR', 8:'LSL', 9:'ROL', 0xa:'DEC', 0xc:'INC', 0xd:'TST', 0xf:'CLR'}.items():
    table[0x00 | i] = (f'{op} <n', '', f'{op}\t<''{}', byte)
    table[0x40 | i] = (f'{op}A', '', f'{op}A')
    table[0x50 | i] = (f'{op}B', '', f'{op}B')
    table[0x60 | i] = (f'{op} ,r', '', f'{op}\t''{}', am_index)
    table[0x70 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)
for i, op in {0:'SUBA', 1:'CMPA', 2:'SBCA', 4:'ANDA', 5:'BITA', 6:'LDA', 8:'EORA', 9:'ADCA', 0xa:'ORA', 0xb:'ADDA'}.items():
    table[0x80 | i] = (f'{op} #n', '', f'{op}\t''#{}', byte)
for i, op in {3:'SUBD', 0xc:'CMPX', 0xe:'LDX'}.items():
    table[0x80 | i] = (f'{op} #nn', '', f'{op}\t''#{}', word)
for i, op in {0:'SUBA', 1:'CMPA', 2:'SBCA', 3:'SUBD', 4:'ANDA', 5:'BITA', 6:'LDA', 7:'STA', 8:'EORA', 9:'ADCA', 0xa:'ORA', 0xb:'ADDA', 0xc:'CMPX', 0xe:'LDX', 0xf:'STX'}.items():
    table[0x90 | i] = (f'{op} <n', '', f'{op}\t<''{}', byte)
    table[0xa0 | i] = (f'{op} ,r', '', f'{op}\t''{}', am_index)
    table[0xb0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)
for i, op in {0:'SUBB', 1:'CMPB', 2:'SBCB', 4:'ANDB', 5:'BITB', 6:'LDB', 8:'EORB', 9:'ADCB', 0xa:'ORB', 0xb:'ADDB'}.items():
    table[0xc0 | i] = (f'{op} #n', '', f'{op}\t''#{}', byte)
for i, op in {3:'ADDD', 0xc:'LDD', 0xe:'LDU'}.items():
    table[0xc0 | i] = (f'{op} #nn', '', f'{op}\t''#{}', word)
for i, op in enumerate(('SUBB', 'CMPB', 'SBCB', 'ADDD', 'ANDB', 'BITB', 'LDB', 'STB', 'EORB', 'ADCB', 'ORB', 'ADDB', 'LDD', 'STD', 'LDU', 'STU')):
    table[0xd0 | i] = (f'{op} <n', '', f'{op}\t<''{}', byte)
    table[0xe0 | i] = (f'{op} ,r', '', f'{op}\t''{}', am_index)
    table[0xf0 | i] = (f'{op} >nn', '', f'{op}\t''{}', word)

def op():
    global flags, table
    opcode = fetch()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[1]
    operands = [f() for f in t[3:]]
    return t[2].lower().format(*operands) if '' not in operands else ''

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
    print(f'\t\t\t*\tMC6809 disassembler', file=file)
    print(f'\t\t\t*\tfilename: {args[0]}', file=file)
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t\torg\t${start:0=4x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMC6809 disassembler', file=file)
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

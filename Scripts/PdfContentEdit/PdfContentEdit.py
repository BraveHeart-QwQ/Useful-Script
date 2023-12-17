import os

# TODO 支持中途退出、指定位置开始

with open('Scripts/PdfContentEdit/Content.txt', 'r', encoding='utf8') as file:
    content = file.readlines()
content = [line.rstrip('\n') for line in content] # 去除尾部换行符

print('---------- begin ----------')
result = []
for line in content:
    print(f'{line}\t', end='')
    # page = input('{}  '.format(line))
    page = input()
    result.append('{}\t{}'.format(line, page))
    print('\t{}'.format(page))

print('---------- result ----------')
print(result)

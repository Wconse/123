#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
РАБОЧИЙ ПАРСЕР АУКЦИОНА ДЖАГГЕРНАУТ

Формат: <разделитель> <имя_поля_ASCII> <маркер_типа_04/05/06> <значение>
"""

import binascii
import struct
import json
import sys

def parse_auction(data: bytes) -> dict:
    """Парсит данные аукциона"""
    result = {}
    i = 0
    
    while i < len(data) - 5:
        # Ищем ASCII текст перед маркером типа
        # Читаем вперёд пока не найдём маркер типа
        
        # Проверяем следующие 2-50 байт на наличие ASCII + type marker
        for name_len in range(2, min(51, len(data) - i)):
            # Проверяем что на позиции i+name_len есть маркер типа
            if i + name_len < len(data) and data[i + name_len] in [0x04, 0x05, 0x06]:
                # Проверяем что перед маркером ASCII текст
                name_bytes = data[i:i+name_len]
                
                # ASCII проверка
                if all(33 <= b < 127 for b in name_bytes):
                    try:
                        name = name_bytes.decode('ascii')
                        
                        # Проверяем что это похоже на имя поля
                        alpha_count = sum(c.isalpha() for c in name)
                        if alpha_count >= 2 and '_' not in name[:1]:  # Не начинается с _
                            type_marker = data[i + name_len]
                            type_pos = i + name_len
                            value = None
                            next_pos = type_pos + 1
                            
                            # Читаем значение
                            if type_marker == 0x04:  # Int
                                if type_pos + 1 < len(data):
                                    value = data[type_pos + 1]
                                    next_pos = type_pos + 2
                            
                            elif type_marker == 0x05:  # Double
                                if type_pos + 9 <= len(data):
                                    try:
                                        value = struct.unpack('>d', data[type_pos+1:type_pos+9])[0]
                                        next_pos = type_pos + 9
                                    except:
                                        pass
                            
                            elif type_marker == 0x06:  # String
                                if type_pos + 2 < len(data):
                                    str_len = data[type_pos + 1]
                                    if type_pos + 2 + str_len <= len(data):
                                        try:
                                            value = data[type_pos+2:type_pos+2+str_len].decode('utf-8', errors='ignore')
                                            next_pos = type_pos + 2 + str_len
                                        except:
                                            pass
                            
                            if value is not None:
                                result[name] = value
                                i = next_pos
                                break
                    except:
                        pass
        else:
            i += 1
    
    return result

def detect_encoding(file_path):
    """Определяет кодировку файла по BOM"""
    with open(file_path, 'rb') as f:
        start = f.read(4)
    
    if start.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    elif start.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    elif start.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    else:
        return 'utf-8'

def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = 'responses_utf8.txt'
    
    print("=" * 100)
    print(" " * 32 + "ПАРСЕР АУКЦИОНА ДЖАГГЕРНАУТ")
    print("=" * 100)
    print()
    
    # Определяем кодировку
    encoding = detect_encoding(input_file)
    print(f"Определена кодировка: {encoding}\n")
    
    all_lots = []
    
    with open(input_file, 'r', encoding=encoding) as f:
        lines = [l.strip() for l in f if l.strip()]
    
    for lot_num, line in enumerate(lines, 1):
        print(f"{'─' * 100}")
        print(f"ЛОТ #{lot_num}")
        print(f"{'─' * 100}\n")
        
        # Парсим hex
        if '\t' in line:
            _, hex_str = line.split('\t', 1)
        else:
            hex_str = line
        
        try:
            data = binascii.unhexlify(hex_str)
            lot_data = parse_auction(data)
            lot_data['_lot_number'] = lot_num
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            lot_data = {'error': str(e), '_lot_number': lot_num}
        
        # Категоризируем и выводим
        if lot_data and len(lot_data) > 1:
            # Аукцион
            auction_fields = ['id', 'price', 'buyout', 'bid', 'rtime', 'status']
            print("  💰 АУКЦИОН:")
            for key in auction_fields:
                if key in lot_data:
                    val = lot_data[key]
                    if isinstance(val, float):
                        print(f"     {key:20s} = {val:.2f}")
                    else:
                        print(f"     {key:20s} = {str(val)[:70]}")
            
            # Предмет
            item_fields = ['title', 'picture', 'artifact', 'durability', 'quality', 
                          'level_min', 'level_max', 'ctime']
            has_item = any(k in lot_data for k in item_fields)
            if has_item:
                print("\n  ⚔️  ПРЕДМЕТ:")
                for key in item_fields:
                    if key in lot_data:
                        val = lot_data[key]
                        v_str = f"{val:.2f}" if isinstance(val, float) else str(val)[:70]
                        print(f"     {key:20s} = {v_str}")
            
            # Продавец
            seller_fields = ['user_id', 'user_nick', 'nick', 'level', 'clan_title']
            has_seller = any(k in lot_data for k in seller_fields)
            if has_seller:
                print("\n  👤 ПРОДАВЕЦ:")
                for key in seller_fields:
                    if key in lot_data:
                        print(f"     {key:20s} = {str(lot_data[key])[:70]}")
            
            # Остальное
            shown = set(auction_fields + item_fields + seller_fields + ['_lot_number', 'error'])
            other = {k: v for k, v in lot_data.items() if k not in shown}
            if other:
                print(f"\n  📊 ДОПОЛНИТЕЛЬНО ({len(other)} полей):")
                for key in sorted(list(other.keys())[:8]):
                    val = other[key]
                    v_str = f"{val:.2f}" if isinstance(val, float) else str(val)[:60]
                    print(f"     {key:20s} = {v_str}")
                if len(other) > 8:
                    print(f"     ...ещё {len(other) - 8} полей")
        else:
            print("  ⚠️  Данные не распарсились")
        
        print()
        all_lots.append(lot_data)
    
    # Сохраняем
    output_file = 'auction_parsed.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_lots, f, ensure_ascii=False, indent=2)
    
    print(f"{'=' * 100}")
    print(f"✅ Обработано: {len(all_lots)} лотов")
    print(f"💾 Сохранено в: {output_file}")
    
    # Статистика
    all_fields = set()
    for lot in all_lots:
        all_fields.update(k for k in lot.keys() if not k.startswith('_') and k != 'error')
    
    print(f"\n📊 СТАТИСТИКА:")
    print(f"   Всего уникальных полей: {len(all_fields)}")
    if all_fields:
        fields_list = sorted(list(all_fields))
        print(f"   Поля: {', '.join(fields_list[:20])}")
        if len(fields_list) > 20:
            print(f"   ...и ещё {len(fields_list) - 20}")
    
    print(f"{'=' * 100}\n")
    
    return all_lots

if __name__ == '__main__':
    lots = main()

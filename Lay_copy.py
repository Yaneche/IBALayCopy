#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
УНИВЕРСАЛЬНЫЙ СКРИПТ ДЛЯ КОПИРОВАНИЯ LAYOUT
Работает с файлами .lay

Логика работы:
1. Выбираем исходный layout (откуда копируем)
2. Выбираем целевой layout (куда копируем или создаем новый)
3. Для каждого индекса из исходного layout выбираем, 
   в какой индекс целевого layout его преобразовать

Особенности:
- Промежуточные файлы сохраняются без расширения (или с .tmp)
- Финальный файл сохраняется с расширением .lay
- Возможность отката к любому промежуточному состоянию
"""

import xml.etree.ElementTree as ET
import re
import uuid
import os
from datetime import datetime

# Глобальные переменные для сохранения состояния
current_tree = None
current_root = None
current_file = None
temp_files = []  # Список временных файлов (путь, описание, время)
last_operation = None  # Последняя операция

def extract_all_indices(xml_str):
    """Извлекает все уникальные индексы из XML"""
    indices = set(re.findall(r'\[(\d+)[:.]', xml_str))
    return sorted(indices, key=int)

def fix_indices(text, source_prefix, target_prefix):
    """
    Заменяет индексы сигналов с префикса source_prefix на target_prefix
    """
    pattern1 = re.compile(rf'\[{source_prefix}:(\d+)\]')
    text = pattern1.sub(f'[{target_prefix}:\\1]', text)
    
    pattern2 = re.compile(rf'\[{source_prefix}\.(\d+)\]')
    text = pattern2.sub(f'[{target_prefix}.\\1]', text)
    
    return text

def create_layout_copy(source_layout, new_name, new_guid, replacement_map):
    """
    Создает копию layout с новым именем и GUID, заменяя указанные индексы
    """
    new_layout = ET.fromstring(ET.tostring(source_layout))
    new_layout.set('Name', new_name)
    new_layout.set('Guid', new_guid)
    
    xml_str = ET.tostring(new_layout, encoding='unicode')
    
    for src, tgt in replacement_map.items():
        if src != tgt:
            print(f"   🔄 Замена: {src} → {tgt}")
            xml_str = fix_indices(xml_str, src, tgt)
    
    return ET.fromstring(xml_str)

def save_temp_file(description):
    """Сохраняет текущее состояние во временный файл (без расширения)"""
    global current_tree, current_file, temp_files
    
    if current_tree is None or current_file is None:
        return None
    
    base_name = os.path.splitext(current_file)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Сохраняем без расширения
    temp_file = f"{base_name}_temp_{timestamp}_{description}"
    
    # Альтернатива с расширением .tmp (раскомментировать если нужно)
    # temp_file = f"{base_name}_temp_{timestamp}_{description}.tmp"
    
    try:
        current_tree.write(temp_file, encoding='utf-8', xml_declaration=True)
        temp_files.append((temp_file, description, datetime.now()))
        print(f"   💾 Промежуточный файл: {temp_file}")
        return temp_file
    except Exception as e:
        print(f"   ❌ Ошибка при сохранении: {e}")
        return None

def cleanup_temp_files():
    """Удаляет все временные файлы"""
    global temp_files
    
    if not temp_files:
        return
    
    print("\n🗑️  Удаление временных файлов:")
    for file, desc, _ in temp_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"   ✅ Удален: {file}")
            except Exception as e:
                print(f"   ❌ Ошибка при удалении {file}: {e}")

def list_all_layouts(root):
    """Показывает все layout в файле"""
    layouts = root.findall('Layout')
    
    print("\n📋 Все layout в файле:")
    for i, layout in enumerate(layouts, 1):
        name = layout.get('Name', 'Без имени')
        guid = layout.get('Guid', 'Нет GUID')
        xml_str = ET.tostring(layout, encoding='unicode')
        indices = extract_all_indices(xml_str)
        
        print(f"   {i}. {name}")
        print(f"      GUID: {guid}")
        if indices:
            print(f"      Индексы: {', '.join(indices)}")
    
    return layouts

def select_source_layout():
    """Выбор исходного layout"""
    global current_root
    
    if current_root is None:
        return None
    
    all_layouts = list_all_layouts(current_root)
    
    if not all_layouts:
        print("❌ В файле нет layout!")
        return None
    
    try:
        source_idx = int(input("\n🔍 Выберите номер layout для КОПИРОВАНИЯ (откуда, 0 - отмена): ")) - 1
        if source_idx == -1:
            return None
        if source_idx < 0 or source_idx >= len(all_layouts):
            print("❌ Неверный номер!")
            return None
        
        source_layout = all_layouts[source_idx]
        source_name = source_layout.get('Name', 'Неизвестно')
        xml_str = ET.tostring(source_layout, encoding='unicode')
        source_indices = extract_all_indices(xml_str)
        
        print(f"✅ Выбран источник: {source_name}")
        print(f"📊 Индексы источника: {', '.join(source_indices)}")
        
        return {
            'layout': source_layout,
            'name': source_name,
            'indices': source_indices
        }
    except ValueError:
        print("❌ Неверный ввод!")
        return None

def select_target_layout(source_name, source_indices):
    """
    Выбор целевого layout, используя уже полученную информацию
    source_name - имя исходного layout (чтобы исключить его)
    source_indices - индексы исходного layout (для информации)
    """
    global current_root
    
    if current_root is None:
        return None
    
    all_layouts = current_root.findall('Layout')
    
    print("\n🎯 Доступные цели:")
    target_info = []
    
    for i, layout in enumerate(all_layouts):
        name = layout.get('Name', 'Без имени')
        # Исключаем исходный layout
        if name == source_name:
            continue
            
        xml_str = ET.tostring(layout, encoding='unicode')
        indices = extract_all_indices(xml_str)
        
        print(f"   {len(target_info) + 1}. {name}")
        print(f"      Индексы: {', '.join(indices)}")
        target_info.append({
            'layout': layout,
            'name': name,
            'indices': indices
        })
    
    if not target_info:
        print("❌ Нет доступных целей!")
        return None
    
    try:
        target_choice = int(input("\n🎯 Выберите номер целевого layout (0 - отмена): ")) - 1
        if target_choice == -1:
            return None
        if target_choice < 0 or target_choice >= len(target_info):
            print("❌ Неверный номер!")
            return None
        
        target = target_info[target_choice]
        print(f"✅ Выбрана цель: {target['name']}")
        print(f"📊 Индексы цели: {', '.join(target['indices'])}")
        
        return target
    except ValueError:
        print("❌ Неверный ввод!")
        return None

def map_indices_interactive(source_indices, target_indices, target_name):
    """
    Интерактивное сопоставление индексов
    Для каждого индекса из источника выбираем, в какой индекс цели его преобразовать
    """
    print(f"\n🔧 Настройка преобразования индексов для {target_name}")
    print("=" * 70)
    
    replacement_map = {}
    
    for i, src_idx in enumerate(source_indices):
        print(f"\n📊 Индекс {i+1} из источника: {src_idx}")
        print("   Доступные целевые индексы:")
        
        # Показываем доступные целевые индексы
        for j, tgt_idx in enumerate(target_indices):
            status = "✅" if tgt_idx in replacement_map.values() else "🆓"
            print(f"      {j+1}. {status} {tgt_idx}")
        
        print("   Варианты:")
        print("      - Введите номер целевого индекса")
        print("      - 'new N' - создать новый индекс N")
        print("      - 'skip' - пропустить (не заменять)")
        print("      - '0' - отмена")
        
        while True:
            choice = input(f"\n👉 Индекс {src_idx} → ?: ").strip().lower()
            
            if choice == '0':
                return None
            
            if choice == 'skip':
                print(f"   ⏭️  Индекс {src_idx} пропущен")
                break
            
            if choice.startswith('new '):
                try:
                    new_idx = choice[4:].strip()
                    # Проверяем, что это число
                    int(new_idx)
                    if new_idx in replacement_map.values():
                        print(f"   ⚠️ Индекс {new_idx} уже используется в этом layout!")
                        continue
                    replacement_map[src_idx] = new_idx
                    print(f"   ✅ {src_idx} → {new_idx} (новый индекс)")
                    break
                except ValueError:
                    print("   ❌ Неверный формат. Используйте 'new 5'")
                    continue
            
            try:
                choice_num = int(choice) - 1
                if 0 <= choice_num < len(target_indices):
                    tgt_idx = target_indices[choice_num]
                    if tgt_idx in replacement_map.values():
                        print(f"   ⚠️ Индекс {tgt_idx} уже используется!")
                        continue
                    replacement_map[src_idx] = tgt_idx
                    print(f"   ✅ {src_idx} → {tgt_idx}")
                    break
                else:
                    print(f"   ❌ Номер должен быть от 1 до {len(target_indices)}")
            except ValueError:
                print("   ❌ Неверный ввод!")
    
    return replacement_map

def copy_to_existing():
    """Режим 1: копирование в существующий layout"""
    global current_tree, current_root, current_file, last_operation
    
    if current_root is None:
        print("\n❌ Сначала загрузите файл!")
        input("Нажмите Enter для продолжения...")
        return
    
    # Выбираем источник
    source = select_source_layout()
    if source is None:
        return
    
    # Выбираем цель, передавая имя источника
    target = select_target_layout(source['name'], source['indices'])
    if target is None:
        return
    
    # Интерактивное сопоставление индексов
    replacement_map = map_indices_interactive(
        source['indices'], 
        target['indices'],
        target['name']
    )
    
    if replacement_map is None:
        print("❌ Операция отменена.")
        input("Нажмите Enter для продолжения...")
        return
    
    if not replacement_map:
        print("❌ Не выбрано ни одного преобразования!")
        input("Нажмите Enter для продолжения...")
        return
    
    # Генерируем новый GUID
    new_guid = str(uuid.uuid4())
    
    # Показываем итоговую карту замены
    print("\n" + "=" * 70)
    print("   ИТОГОВАЯ КАРТА ПРЕОБРАЗОВАНИЯ")
    print("=" * 70)
    for src, tgt in replacement_map.items():
        print(f"   {src} → {tgt}")
    
    # Подтверждение
    confirm = input("\n✅ Подтвердить замену? (да/нет): ").strip().lower()
    if confirm not in ('да', 'yes', 'y'):
        print("❌ Операция отменена.")
        input("Нажмите Enter для продолжения...")
        return
    
    # Создаем копию с новыми индексами
    print("\n🔄 Создание копии...")
    new_layout = create_layout_copy(
        source['layout'], 
        target['name'], 
        new_guid, 
        replacement_map
    )
    
    # Заменяем существующий layout
    for i, layout in enumerate(current_root.findall('Layout')):
        if layout.get('Name') == target['name']:
            current_root.remove(layout)
            current_root.insert(i, new_layout)
            print(f"   ✅ Layout '{target['name']}' заменен")
            break
    
    # Сохраняем промежуточный файл
    desc = f"replace_{source['name']}_to_{target['name']}"
    save_temp_file(desc)
    last_operation = desc
    
    print(f"\n✅ Операция выполнена.")
    input("\nНажмите Enter для продолжения...")


def create_new():
    """Режим 2: создание нового layout"""
    global current_tree, current_root, current_file, last_operation  # ← ЭТО ДОЛЖНО БЫТЬ ПЕРВОЙ СТРОКОЙ

    if current_root is None:
        print("\n❌ Сначала загрузите файл!")
        input("Нажмите Enter для продолжения...")
        return

    # Выбираем источник
    source = select_source_layout()
    if source is None:
        return

    # Вводим название нового layout
    print("\n" + "=" * 70)
    print("   ПАРАМЕТРЫ НОВОГО LAYOUT")
    print("=" * 70)

    target_name = input("📝 Название нового layout (0 - отмена): ").strip()
    if target_name == '0':
        return
    if not target_name:
        print("❌ Название не может быть пустым!")
        input("Нажмите Enter для продолжения...")
        return

    # Проверяем, нет ли уже такого названия
    existing_names = [l.get('Name') for l in current_root.findall('Layout')]
    if target_name in existing_names:
        print(f"❌ Layout с именем '{target_name}' уже существует!")
        input("Нажмите Enter для продолжения...")
        return

    # Получаем все существующие индексы в файле
    all_indices = set()
    for layout in current_root.findall('Layout'):
        xml_str = ET.tostring(layout, encoding='unicode')
        all_indices.update(extract_all_indices(xml_str))
    all_indices = sorted(all_indices, key=int)

    print(f"\n📊 Существующие индексы в файле: {', '.join(all_indices)}")

    # Для каждого индекса из источника выбираем целевой
    print(f"\n🔧 Настройка индексов для нового layout '{target_name}'")
    print("=" * 70)

    replacement_map = {}

    for i, src_idx in enumerate(source['indices']):
        print(f"\n📊 Индекс {i + 1} из источника: {src_idx}")
        print("   Варианты:")
        print("      - Введите номер существующего индекса из списка выше")
        print("      - 'new N' - создать новый индекс N")
        print("      - 'same' - оставить тот же индекс")
        print("      - '0' - отмена")

        while True:
            choice = input(f"\n👉 Индекс {src_idx} → ?: ").strip().lower()

            if choice == '0':
                return

            if choice == 'same':
                replacement_map[src_idx] = src_idx
                print(f"   ✅ {src_idx} → {src_idx} (без изменений)")
                break

            if choice.startswith('new '):
                try:
                    new_idx = choice[4:].strip()
                    int(new_idx)  # Проверка что число
                    if new_idx in replacement_map.values():
                        print(f"   ⚠️ Индекс {new_idx} уже используется в этом layout!")
                        continue
                    replacement_map[src_idx] = new_idx
                    print(f"   ✅ {src_idx} → {new_idx} (новый индекс)")
                    break
                except ValueError:
                    print("   ❌ Неверный формат. Используйте 'new 5'")
                    continue

            try:
                # Пользователь ввел число - ищем в существующих индексах
                choice_num = int(choice)
                choice_str = str(choice_num)

                if choice_str in replacement_map.values():
                    print(f"   ⚠️ Индекс {choice_str} уже используется в этом layout!")
                    continue

                if choice_str in all_indices:
                    replacement_map[src_idx] = choice_str
                    print(f"   ✅ {src_idx} → {choice_str}")
                    break
                else:
                    print(f"   ❌ Индекс {choice_str} не найден среди существующих!")
                    print(f"      Доступны: {', '.join(all_indices)}")
            except ValueError:
                print("   ❌ Неверный ввод!")

    if not replacement_map:
        print("❌ Не выбрано ни одного преобразования!")
        input("Нажмите Enter для продолжения...")
        return

    # Генерируем новый GUID
    new_guid = str(uuid.uuid4())

    # Показываем итоговую карту замены
    print("\n" + "=" * 70)
    print("   ИТОГОВАЯ КАРТА ПРЕОБРАЗОВАНИЯ")
    print("=" * 70)
    for src, tgt in replacement_map.items():
        print(f"   {src} → {tgt}")

    # Подтверждение
    confirm = input("\n✅ Подтвердить создание? (да/нет): ").strip().lower()
    if confirm not in ('да', 'yes', 'y'):
        print("❌ Операция отменена.")
        input("Нажмите Enter для продолжения...")
        return

    # Создаем копию с новыми индексами
    print("\n🔄 Создание копии...")
    new_layout = create_layout_copy(
        source['layout'],
        target_name,
        new_guid,
        replacement_map
    )

    # Добавляем новый layout в правильное место - перед служебными тегами
    layouts = current_root.findall('Layout')

    if layouts:
        # Вставляем после последнего Layout
        current_root.insert(len(layouts), new_layout)
        print(f"   ✅ Добавлен новый layout '{target_name}' (вставлен после существующих слоев)")
    else:
        # Если нет Layout, просто добавляем
        current_root.append(new_layout)
        print(f"   ✅ Добавлен новый layout '{target_name}'")

    # Сохраняем промежуточный файл
    desc = f"add_{target_name}_from_{source['name']}"
    save_temp_file(desc)
    last_operation = desc

    print(f"\n✅ Операция выполнена.")
    input("\nНажмите Enter для продолжения...")

def show_temp_files():
    """Показывает историю промежуточных файлов"""
    global temp_files
    
    if not temp_files:
        print("\n📭 Нет промежуточных файлов")
    else:
        print(f"\n📁 Промежуточные файлы ({len(temp_files)}):")
        for i, (file, desc, timestamp) in enumerate(temp_files, 1):
            if os.path.exists(file):
                size = os.path.getsize(file)
                time_str = timestamp.strftime('%H:%M:%S')
                print(f"   {i}. {time_str} - {desc}")
                print(f"      Файл: {file} ({size} байт)")
            else:
                print(f"   {i}. {desc} (ФАЙЛ УДАЛЕН)")
    
    input("\nНажмите Enter для продолжения...")

def create_final_file():
    """Создает финальный .lay файл"""
    global current_tree, current_file
    
    if current_tree is None or current_file is None:
        print("\n❌ Нет загруженного файла!")
        input("Нажмите Enter для продолжения...")
        return
    
    base_name = os.path.splitext(current_file)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_file = f"{base_name}_final_{timestamp}.lay"
    
    try:
        current_tree.write(final_file, encoding='utf-8', xml_declaration=True)
        print(f"\n✅ Финальный файл сохранен: {final_file}")
        
        size = os.path.getsize(final_file)
        print(f"   Размер: {size} байт")
        print(f"   Layout: {len(current_root.findall('Layout'))}")
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении: {e}")
    
    input("\nНажмите Enter для продолжения...")

def undo_last_operation():
    """Откатывает последнюю операцию"""
    global current_tree, current_root, temp_files, last_operation
    
    if len(temp_files) < 2:
        print("\n❌ Нет предыдущего состояния для отката!")
        input("Нажмите Enter для продолжения...")
        return
    
    prev_file, prev_desc, _ = temp_files[-2]
    
    if not os.path.exists(prev_file):
        print(f"\n❌ Промежуточный файл не найден: {prev_file}")
        input("Нажмите Enter для продолжения...")
        return
    
    try:
        current_tree = ET.parse(prev_file)
        current_root = current_tree.getroot()
        
        last_file, last_desc, _ = temp_files[-1]
        if os.path.exists(last_file):
            os.remove(last_file)
            print(f"   🗑️ Удален: {last_file}")
        
        temp_files.pop()
        last_operation = prev_desc
        
        print(f"\n✅ Откат к состоянию: {prev_desc}")
        
    except Exception as e:
        print(f"❌ Ошибка при откате: {e}")
    
    input("\nНажмите Enter для продолжения...")

def show_current_file():
    """Показывает информацию о текущем файле"""
    global current_file, current_root, temp_files
    
    if current_file is None or current_root is None:
        print("\n❌ Файл не загружен")
    else:
        print(f"\n📁 Текущий файл: {current_file}")
        layouts = current_root.findall('Layout')
        print(f"📊 Всего layout: {len(layouts)}")
        
        if temp_files:
            print(f"📝 Промежуточных файлов: {len(temp_files)}")
            if last_operation:
                print(f"🔄 Последняя операция: {last_operation}")
        
        print("\n📋 Детальная информация:")
        for i, layout in enumerate(layouts, 1):
            name = layout.get('Name', 'Без имени')
            guid = layout.get('Guid', 'Нет GUID')
            xml_str = ET.tostring(layout, encoding='unicode')
            indices = extract_all_indices(xml_str)
            
            print(f"\n   {i}. {name}")
            print(f"      GUID: {guid}")
            if indices:
                print(f"      Индексы: {', '.join(indices)}")
    
    input("\nНажмите Enter для продолжения...")

def select_file():
    """Выбор .lay файла"""
    global current_tree, current_root, current_file, temp_files
    
    # Получаем все .lay файлы
    all_files = os.listdir('.')
    lay_files = []
    
    for f in all_files:
        if f.lower().endswith('.lay'):
            # Исключаем временные файлы (содержат _temp_)
            if not ('_temp_' in f):
                lay_files.append(f)
    
    if not lay_files:
        print("\n❌ В текущей папке не найдено .lay файлов!")
        input("Нажмите Enter для продолжения...")
        return False
    
    print("\n📁 Доступные .lay файлы:")
    for i, f in enumerate(lay_files, 1):
        size = os.path.getsize(f)
        modified = datetime.fromtimestamp(os.path.getmtime(f))
        print(f"   {i}. {f} ({size} байт, {modified.strftime('%d.%m.%Y %H:%M')})")
    
    try:
        file_choice = int(input("\n📁 Выберите номер файла (0 - отмена): ")) - 1
        if file_choice == -1:
            return False
        if file_choice < 0 or file_choice >= len(lay_files):
            print("❌ Неверный выбор!")
            input("Нажмите Enter для продолжения...")
            return False
        current_file = lay_files[file_choice]
    except ValueError:
        print("❌ Неверный ввод!")
        input("Нажмите Enter для продолжения...")
        return False
    
    try:
        current_tree = ET.parse(current_file)
        current_root = current_tree.getroot()
        temp_files = []  # Очищаем список временных файлов
        print(f"\n✅ Загружен файл: {current_file}")
        
        # Создаем начальный промежуточный файл
        save_temp_file("start")
        
        input("Нажмите Enter для продолжения...")
        return True
    except Exception as e:
        print(f"❌ Ошибка при чтении файла: {e}")
        input("Нажмите Enter для продолжения...")
        return False

def main():
    """Главное меню программы"""
    while True:
        # Очистка экрана
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 70)
        print("   УНИВЕРСАЛЬНОЕ УПРАВЛЕНИЕ LAYOUT")
        print("=" * 70)
        
        # Показываем текущий файл
        if current_file is not None:
            print(f"📁 Текущий файл: {current_file}")
            if current_root is not None:
                layouts = current_root.findall('Layout')
                print(f"📊 Загружено layout: {len(layouts)}")
                if temp_files:
                    print(f"📝 Промежуточных: {len(temp_files)}")
        else:
            print("📁 Файл не загружен")
        
        print("\n" + "=" * 70)
        print("   ГЛАВНОЕ МЕНЮ")
        print("=" * 70)
        print("   1. 📁 Выбрать .lay файл")
        print("   2. 🔄 Копировать в СУЩЕСТВУЮЩИЙ layout (замена)")
        print("   3. ✨ Создать НОВЫЙ layout (добавление)")
        print("   4. 📜 Показать промежуточные файлы")
        print("   5. ↩️  Откатить последнюю операцию")
        print("   6. 💾 Создать финальный .lay файл")
        print("   7. ℹ️  Информация о текущем файле")
        print("   0. 🚪 Выход")
        print("=" * 70)
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '1':
            select_file()
        elif choice == '2':
            copy_to_existing()
        elif choice == '3':
            create_new()
        elif choice == '4':
            show_temp_files()
        elif choice == '5':
            undo_last_operation()
        elif choice == '6':
            create_final_file()
        elif choice == '7':
            show_current_file()
        elif choice == '0':
            if temp_files:
                clean = input("\n🗑️  Удалить все промежуточные файлы? (да/нет): ").strip().lower()
                if clean in ('да', 'yes', 'y'):
                    cleanup_temp_files()
            print("\n👋 Выход из программы.")
            break
        else:
            print("\n❌ Неверный выбор!")
            input("Нажмите Enter для продолжения...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("Нажмите Enter для выхода...")
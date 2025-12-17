#!/usr/bin/env python3
"""
Интерактивен инструмент за ръчна синхронизация на текстове с аудио
Позволява на потребителя да слуша песента и да маркира моментите, когато започва всеки ред
"""

import json
import os
from datetime import timedelta
from moviepy.editor import AudioFileClip

def format_time(seconds):
    """Форматира секунди в MM:SS.mmm формат"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    milliseconds = int((td.total_seconds - total_seconds) * 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def parse_time(time_str):
    """Парсва време от формат MM:SS.mmm в секунди"""
    parts = time_str.split(':')
    minutes = int(parts[0])
    seconds_parts = parts[1].split('.')
    seconds = int(seconds_parts[0])
    milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
    return minutes * 60 + seconds + milliseconds / 1000.0

def load_lyrics(lyrics_file):
    """Зарежда текстовете от файла"""
    with open(lyrics_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    lyrics_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('//'):
            lyrics_lines.append(line)
    
    return lyrics_lines

def save_sync_data(sync_data, output_file='sync_data.json'):
    """Запазва синхронизационните данни"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sync_data, f, indent=2, ensure_ascii=False)
    print(f"\nДанните са запазени в: {output_file}")

def load_sync_data(input_file='sync_data.json'):
    """Зарежда съхранени синхронизационни данни"""
    if os.path.exists(input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def create_timeline_from_sync(sync_data, lyrics_lines, duration):
    """Създава таймлайн от синхронизационните данни"""
    timeline = []
    
    for i, line in enumerate(lyrics_lines):
        if i < len(sync_data['timestamps']):
            start = sync_data['timestamps'][i]
            
            # Крайът е следващият timestamp или края на песента
            if i + 1 < len(sync_data['timestamps']):
                end = sync_data['timestamps'][i + 1]
            else:
                end = duration
            
            timeline.append({
                'line': line,
                'start': start,
                'end': end
            })
        else:
            # Ако няма timestamp, използваме приблизително време
            timeline.append({
                'line': line,
                'start': 0,
                'end': duration
            })
    
    return timeline

def export_timeline(timeline, output_file='Timeline.md'):
    """Експортира таймлайна в Markdown формат"""
    section_names = {
        'intro': 'Встъп',
        'verse1': 'Верс 1',
        'chorus1': 'Припев 1',
        'interlude': 'Интерлюд',
        'verse2': 'Верс 2',
        'chorus2': 'Припев 2',
        'chorus3': 'Припев 3',
        'outro': 'Финал'
    }
    
    # Определяне на секциите
    structure = [
        {'type': 'intro', 'lines': 1},
        {'type': 'verse1', 'lines': 16},
        {'type': 'chorus1', 'lines': 2},
        {'type': 'interlude', 'lines': 1},
        {'type': 'verse2', 'lines': 8},
        {'type': 'chorus2', 'lines': 2},
        {'type': 'chorus3', 'lines': 2},
        {'type': 'outro', 'lines': 1},
    ]
    
    line_idx = 0
    for section in structure:
        for _ in range(section['lines']):
            if line_idx < len(timeline):
                timeline[line_idx]['section'] = section['type']
                line_idx += 1
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# FAKE NEWS - Таймлайн с таймкодове (Ръчна синхронизация)\n\n")
        f.write("---\n\n")
        
        current_section = None
        for i, entry in enumerate(timeline, 1):
            start_time = format_time(entry['start'])
            end_time = format_time(entry['end'])
            duration = format_time(entry['end'] - entry['start'])
            
            section_type = entry.get('section', 'unknown')
            if section_type != current_section:
                current_section = section_type
                section_name = section_names.get(section_type, section_type)
                f.write(f"\n### {section_name.upper()}\n\n")
            
            f.write(f"## {i}. {start_time} - {end_time} ({duration})\n")
            f.write(f"**Текст:** {entry['line']}\n\n")
    
    print(f"\nТаймлайнът е експортиран в: {output_file}")

def interactive_sync(audio_file, lyrics_file):
    """Интерактивен режим за синхронизация"""
    print("=" * 60)
    print("ИНТЕРАКТИВНА СИНХРОНИЗАЦИЯ НА ТЕКСТОВЕ")
    print("=" * 60)
    print()
    
    # Зареждане на данни
    lyrics_lines = load_lyrics(lyrics_file)
    audio = AudioFileClip(audio_file)
    duration = audio.duration
    
    print(f"Песен: {audio_file}")
    print(f"Продължителност: {format_time(duration)}")
    print(f"Брой редове: {len(lyrics_lines)}")
    print()
    
    # Проверка за съхранени данни
    sync_data = load_sync_data()
    if sync_data:
        print(f"Намерени съхранени данни с {len(sync_data.get('timestamps', []))} timestamp-а")
        use_existing = input("Да използвам ли съхранените данни? (y/n): ").lower().strip()
        if use_existing == 'y':
            timestamps = sync_data['timestamps']
        else:
            timestamps = []
    else:
        timestamps = []
    
    print()
    print("ИНСТРУКЦИИ:")
    print("- Слушай песента и натискай SPACE, когато започва всеки ред")
    print("- Натисни 'r' за да повториш текущия ред")
    print("- Натисни 's' за да спреш и запазиш прогреса")
    print("- Натисни 'q' за да излезеш без запазване")
    print("- Натисни 'p' за да видиш текущия прогрес")
    print()
    
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(audio_file)
        
        current_line = len(timestamps)
        
        print(f"\nЗапочване от ред {current_line + 1}/{len(lyrics_lines)}")
        print(f"Текст: {lyrics_lines[current_line] if current_line < len(lyrics_lines) else 'КРАЙ'}")
        print("\nНатисни SPACE за да започнеш...")
        
        input()  # Чакане за старт
        
        pygame.mixer.music.play()
        start_time = pygame.time.get_ticks() / 1000.0
        
        running = True
        while running and current_line < len(lyrics_lines):
            import sys
            import select
            import tty
            import termios
            
            # Неблокиращо четене на клавиатурата
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    
                    if key == ' ':  # SPACE - маркиране на timestamp
                        current_time = (pygame.time.get_ticks() / 1000.0) - start_time
                        timestamps.append(current_time)
                        print(f"\n[{format_time(current_time)}] Ред {current_line + 1}: {lyrics_lines[current_line]}")
                        current_line += 1
                        
                        if current_line < len(lyrics_lines):
                            print(f"\nСледващ ред ({current_line + 1}/{len(lyrics_lines)}): {lyrics_lines[current_line]}")
                        else:
                            print("\n✓ Всички редове са маркирани!")
                            running = False
                    
                    elif key == 'r':  # Repeat
                        pygame.mixer.music.stop()
                        pygame.mixer.music.play()
                        start_time = pygame.time.get_ticks() / 1000.0
                        print("\n↻ Повторение...")
                    
                    elif key == 's':  # Save
                        sync_data = {'timestamps': timestamps}
                        save_sync_data(sync_data)
                        print("\n💾 Прогресът е запазен!")
                    
                    elif key == 'p':  # Progress
                        print(f"\n📊 Прогрес: {current_line}/{len(lyrics_lines)} реда")
                        if timestamps:
                            print(f"Последен timestamp: {format_time(timestamps[-1])}")
                    
                    elif key == 'q':  # Quit
                        running = False
                        print("\n❌ Изход без запазване")
                
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        pygame.mixer.music.stop()
        
        if len(timestamps) == len(lyrics_lines):
            print("\n✓ Успешна синхронизация!")
            sync_data = {'timestamps': timestamps}
            save_sync_data(sync_data)
            
            timeline = create_timeline_from_sync(sync_data, lyrics_lines, duration)
            export_timeline(timeline)
        else:
            print(f"\n⚠ Синхронизирани са само {len(timestamps)} от {len(lyrics_lines)} реда")
            if timestamps:
                save_choice = input("Да запазя ли прогреса? (y/n): ").lower().strip()
                if save_choice == 'y':
                    sync_data = {'timestamps': timestamps}
                    save_sync_data(sync_data)
    
    except ImportError:
        print("\nГРЕШКА: pygame не е инсталиран")
        print("Инсталирай го с: pip install pygame")
        print("\nАлтернативно, можеш да използваш текстов режим...")
        text_mode_sync(audio_file, lyrics_lines, duration)

def text_mode_sync(audio_file, lyrics_lines, duration):
    """Текстов режим за синхронизация (без pygame)"""
    print("\nТЕКСТОВ РЕЖИМ ЗА СИНХРОНИЗАЦИЯ")
    print("=" * 60)
    print("\nЩе трябва да въвеждаш таймкодовете ръчно.")
    print("Формат: MM:SS.mmm (например: 00:15.500)")
    print()
    
    timestamps = []
    
    for i, line in enumerate(lyrics_lines):
        print(f"\nРед {i+1}/{len(lyrics_lines)}: {line}")
        
        while True:
            time_input = input(f"Въведи начален таймкод (или 'skip' за пропускане): ").strip()
            
            if time_input.lower() == 'skip':
                break
            
            try:
                timestamp = parse_time(time_input)
                if 0 <= timestamp <= duration:
                    timestamps.append(timestamp)
                    print(f"✓ Записан: {format_time(timestamp)}")
                    break
                else:
                    print(f"⚠ Таймкодът трябва да е между 00:00.000 и {format_time(duration)}")
            except:
                print("⚠ Невалиден формат. Използвай MM:SS.mmm")
    
    if timestamps:
        sync_data = {'timestamps': timestamps}
        save_sync_data(sync_data)
        
        timeline = create_timeline_from_sync(sync_data, lyrics_lines, duration)
        export_timeline(timeline)
        print(f"\n✓ Синхронизирани са {len(timestamps)} реда")

def main():
    audio_file = 'FakeNews.wav'
    lyrics_file = 'Lyrics.md'
    
    import os
    if not os.path.exists(audio_file):
        audio_file = 'FakeNews.mp3'
    
    if not os.path.exists(audio_file):
        print(f"ГРЕШКА: Не е намерен аудио файл")
        return
    
    if not os.path.exists(lyrics_file):
        print(f"ГРЕШКА: Не е намерен файл с текстове")
        return
    
    # Проверка за pygame
    try:
        import pygame
        interactive_sync(audio_file, lyrics_file)
    except ImportError:
        print("pygame не е инсталиран. Използва се текстов режим...")
        lyrics_lines = load_lyrics(lyrics_file)
        audio = AudioFileClip(audio_file)
        duration = audio.duration
        text_mode_sync(audio_file, lyrics_lines, duration)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрекратено от потребителя")
    except Exception as e:
        print(f"ГРЕШКА: {e}")
        import traceback
        traceback.print_exc()


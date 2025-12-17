#!/usr/bin/env python3
"""
Скрипт за създаване на примерен видеоклип с синхронизирани текстове
"""

import re
from moviepy.editor import (
    AudioFileClip, 
    TextClip, 
    CompositeVideoClip, 
    ColorClip,
    concatenate_videoclips
)
from datetime import timedelta

def parse_time(time_str):
    """Парсва време от формат MM:SS.mmm в секунди"""
    parts = time_str.split(':')
    minutes = int(parts[0])
    seconds_parts = parts[1].split('.')
    seconds = int(seconds_parts[0])
    milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
    return minutes * 60 + seconds + milliseconds / 1000.0

def parse_timeline(timeline_file):
    """Парсва Timeline.md файла и извлича таймкодовете"""
    timeline = []
    current_section = None
    
    with open(timeline_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Намиране на секции и записи
    section_pattern = r'###\s+([^\n]+)'
    entry_pattern = r'##\s+\d+\.\s+(\d{2}:\d{2}\.\d{3})\s+-\s+(\d{2}:\d{2}\.\d{3})[^\n]*\n\*\*Текст:\*\*\s+([^\n]+)'
    
    sections = re.finditer(section_pattern, content)
    entries = re.finditer(entry_pattern, content)
    
    # Създаване на списък с секции и техните позиции
    section_list = []
    for match in sections:
        section_list.append((match.start(), match.group(1).strip()))
    
    # Обработка на записите
    for entry_match in entries:
        start_time = parse_time(entry_match.group(1))
        end_time = parse_time(entry_match.group(2))
        text = entry_match.group(3).strip()
        
        # Определяне на секцията
        entry_pos = entry_match.start()
        section = 'Unknown'
        for i, (sec_pos, sec_name) in enumerate(section_list):
            if entry_pos > sec_pos:
                section = sec_name
            else:
                break
        
        timeline.append({
            'start': start_time,
            'end': end_time,
            'text': text,
            'section': section
        })
    
    return timeline

def get_section_color(section):
    """Връща цвят за различните секции"""
    colors = {
        'ВСТЪП': ('black', 'white'),
        'ВЕРС 1': ('#1a1a1a', '#ff4444'),
        'ПРИПЕВ 1': ('#2a0000', '#ff6666'),
        'ИНТЕРЛЮД': ('#000033', '#ffff00'),
        'ВЕРС 2': ('#1a1a1a', '#ff4444'),
        'ПРИПЕВ 2': ('#2a0000', '#ff6666'),
        'ПРИПЕВ 3': ('#2a0000', '#ff6666'),
        'ФИНАЛ': ('#000000', '#ff0000'),
    }
    return colors.get(section, ('black', 'white'))

def create_text_clip(text, start, end, section, size=(1920, 1080)):
    """Създава текстов клип за даден ред"""
    bg_color, text_color = get_section_color(section)
    duration = end - start
    
    # Създаване на фонов клип
    bg = ColorClip(size=size, color=bg_color, duration=duration)
    
    # Подготовка на текста - разделяне на редове ако е твърде дълъг
    max_chars_per_line = 50
    if len(text) > max_chars_per_line:
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars_per_line:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(' '.join(current_line))
        display_text = '\n'.join(lines)
    else:
        display_text = text
    
    # Създаване на текстов клип
    # Опитваме се с 'caption' метод (не изисква ImageMagick)
    try:
        txt_clip = TextClip(
            display_text,
            fontsize=60,
            color=text_color,
            font='Arial-Bold',
            method='caption',
            size=(size[0] - 200, None),
            align='center'
        ).set_duration(duration).set_position(('center', 'center'))
    except Exception:
        # Ако 'caption' не работи, опитваме се с 'label'
        try:
            txt_clip = TextClip(
                display_text,
                fontsize=60,
                color=text_color,
                method='label',
                size=(size[0] - 200, None)
            ).set_duration(duration).set_position(('center', 'center'))
        except Exception:
            # Последен опит - проста версия
            txt_clip = TextClip(
                display_text,
                fontsize=50,
                color=text_color
            ).set_duration(duration).set_position(('center', 'center'))
    
    # Комбиниране на фон и текст
    video = CompositeVideoClip([bg, txt_clip])
    
    return video.set_start(start)

def create_sample_video(audio_file, timeline_file, output_file='FakeNews_Sample.mp4'):
    """Създава примерен видеоклип"""
    print("Зареждане на таймлайн...")
    timeline = parse_timeline(timeline_file)
    
    print(f"Намерени {len(timeline)} записа")
    print("Зареждане на аудио...")
    audio = AudioFileClip(audio_file)
    duration = audio.duration
    
    print("Създаване на видеоклипове за всеки ред...")
    clips = []
    
    for i, entry in enumerate(timeline):
        print(f"Обработка {i+1}/{len(timeline)}: {entry['text'][:50]}...")
        clip = create_text_clip(
            entry['text'],
            entry['start'],
            entry['end'],
            entry['section']
        )
        clips.append(clip)
    
    print("Комбиниране на клипове...")
    final_video = CompositeVideoClip(clips, size=(1920, 1080)).set_duration(duration)
    
    print("Добавяне на аудио...")
    final_video = final_video.set_audio(audio)
    
    print(f"Експортиране на видео: {output_file}")
    print("Това може да отнеме няколко минути...")
    final_video.write_videofile(
        output_file,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        bitrate='8000k'
    )
    
    print(f"Видеото е готово: {output_file}")
    
    # Почистване
    audio.close()
    final_video.close()
    for clip in clips:
        clip.close()

def main():
    audio_file = 'FakeNews.mp3'  # Използваме MP3 за по-бързо обработване
    timeline_file = 'Timeline.md'
    output_file = 'FakeNews_Sample.mp4'
    
    # Проверка за MP3, ако няма - използваме WAV
    import os
    if not os.path.exists(audio_file):
        audio_file = 'FakeNews.wav'
    
    if not os.path.exists(audio_file):
        print(f"ГРЕШКА: Не е намерен аудио файл: {audio_file}")
        return
    
    if not os.path.exists(timeline_file):
        print(f"ГРЕШКА: Не е намерен таймлайн файл: {timeline_file}")
        return
    
    try:
        create_sample_video(audio_file, timeline_file, output_file)
    except Exception as e:
        print(f"ГРЕШКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()


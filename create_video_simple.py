#!/usr/bin/env python3
"""
Опростена версия за създаване на примерен видеоклип
Използва PIL за създаване на текстови изображения
"""

import re
from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

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
    
    with open(timeline_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Намиране на секции и записи
    section_pattern = r'###\s+([^\n]+)'
    entry_pattern = r'##\s+\d+\.\s+(\d{2}:\d{2}\.\d{3})\s+-\s+(\d{2}:\d{2}\.\d{3})[^\n]*\n\*\*Текст:\*\*\s+([^\n]+)'
    
    sections = list(re.finditer(section_pattern, content))
    entries = list(re.finditer(entry_pattern, content))
    
    # Обработка на записите
    for entry_match in entries:
        start_time = parse_time(entry_match.group(1))
        end_time = parse_time(entry_match.group(2))
        text = entry_match.group(3).strip()
        
        # Определяне на секцията
        entry_pos = entry_match.start()
        section = 'Unknown'
        for sec_match in sections:
            if entry_pos > sec_match.start():
                section = sec_match.group(1).strip()
            else:
                break
        
        timeline.append({
            'start': start_time,
            'end': end_time,
            'text': text,
            'section': section
        })
    
    return timeline

def get_section_colors(section):
    """Връща цветове за различните секции"""
    colors = {
        'ВСТЪП': ((0, 0, 0), (255, 255, 255)),
        'ВЕРС 1': ((26, 26, 26), (255, 68, 68)),
        'ПРИПЕВ 1': ((42, 0, 0), (255, 102, 102)),
        'ИНТЕРЛЮД': ((0, 0, 51), (255, 255, 0)),
        'ВЕРС 2': ((26, 26, 26), (255, 68, 68)),
        'ПРИПЕВ 2': ((42, 0, 0), (255, 102, 102)),
        'ПРИПЕВ 3': ((42, 0, 0), (255, 102, 102)),
        'ФИНАЛ': ((0, 0, 0), (255, 0, 0)),
    }
    return colors.get(section, ((0, 0, 0), (255, 255, 255)))

def create_text_image(text, section, size=(1920, 1080)):
    """Създава изображение с текст"""
    bg_color, text_color = get_section_colors(section)
    
    # Създаване на изображение
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Опит за зареждане на шрифт
    try:
        # Опитваме се с системни шрифтове
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 80)
        except:
            # Използване на default шрифт
            font = ImageFont.load_default()
    
    # Разделяне на текста на редове
    max_width = size[0] - 200
    words = text.split()
    lines = []
    current_line = []
    current_width = 0
    
    for word in words:
        # Измерване на ширината на думата
        try:
            # Нова версия на PIL
            bbox = draw.textbbox((0, 0), word + ' ', font=font)
            word_width = bbox[2] - bbox[0]
        except:
            try:
                # Стара версия на PIL
                word_width = draw.textsize(word + ' ', font=font)[0]
            except:
                # Fallback - приблизителна ширина
                word_width = len(word) * 40
        
        if current_width + word_width <= max_width:
            current_line.append(word)
            current_width += word_width
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_width = word_width
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Рисуване на текста
    total_height = len(lines) * 100
    start_y = (size[1] - total_height) // 2
    
    for i, line in enumerate(lines):
        # Центриране на текста
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
        except:
            try:
                line_width = draw.textsize(line, font=font)[0]
            except:
                line_width = len(line) * 40
        
        x = (size[0] - line_width) // 2
        y = start_y + i * 100
        
        # Рисуване с outline за по-добра четимост
        draw.text((x-2, y-2), line, fill=(0, 0, 0), font=font)
        draw.text((x+2, y+2), line, fill=(0, 0, 0), font=font)
        draw.text((x-2, y+2), line, fill=(0, 0, 0), font=font)
        draw.text((x+2, y-2), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=text_color, font=font)
    
    return img

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
    temp_dir = 'temp_frames'
    os.makedirs(temp_dir, exist_ok=True)
    
    for i, entry in enumerate(timeline):
        print(f"Обработка {i+1}/{len(timeline)}: {entry['text'][:50]}...")
        
        # Създаване на изображение
        img = create_text_image(entry['text'], entry['section'])
        img_path = f"{temp_dir}/frame_{i:04d}.png"
        img.save(img_path)
        
        # Създаване на видеоклип от изображението
        clip_duration = entry['end'] - entry['start']
        clip = ImageClip(img_path, duration=clip_duration).set_start(entry['start'])
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
        bitrate='5000k',
        threads=4
    )
    
    print(f"Видеото е готово: {output_file}")
    
    # Почистване на временни файлове
    print("Почистване на временни файлове...")
    for clip in clips:
        clip.close()
    final_video.close()
    audio.close()
    
    # Изтриване на временни изображения
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

def main():
    audio_file = 'FakeNews.mp3'
    timeline_file = 'Timeline.md'
    output_file = 'FakeNews_Sample.mp4'
    
    # Проверка за MP3, ако няма - използваме WAV
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


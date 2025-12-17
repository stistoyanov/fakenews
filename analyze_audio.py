#!/usr/bin/env python3
"""
Скрипт за анализ на аудио файл и създаване на таймкодове за музикално видео
"""

import librosa
import numpy as np
from datetime import timedelta

def format_time(seconds):
    """Форматира секунди в MM:SS.mmm формат"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def analyze_audio_structure(audio_file):
    """Анализира структурата на аудио файла"""
    print(f"Зареждане на аудио файл: {audio_file}...")
    
    # Зареждане на аудио файла
    y, sr = librosa.load(audio_file, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)
    
    print(f"Продължителност: {format_time(duration)}")
    print(f"Sample rate: {sr} Hz")
    
    # Изчисляване на темпото
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    # Конвертиране на tempo в скалар, ако е масив
    if isinstance(tempo, np.ndarray):
        tempo_value = float(tempo.item()) if tempo.size > 0 else float(tempo[0])
    elif isinstance(tempo, (list, tuple)):
        tempo_value = float(tempo[0]) if len(tempo) > 0 else 120.0
    else:
        tempo_value = float(tempo)
    print(f"Темпо (BPM): {tempo_value:.2f}")
    
    # Анализ на енергията за идентифициране на секции
    # Използваме спектралния център и rolloff за да идентифицираме промени
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    
    # Нормализиране
    spectral_centroids = (spectral_centroids - np.min(spectral_centroids)) / (np.max(spectral_centroids) - np.min(spectral_centroids))
    spectral_rolloff = (spectral_rolloff - np.min(spectral_rolloff)) / (np.max(spectral_rolloff) - np.min(spectral_rolloff))
    
    # Комбинирана метрика за промени в структурата
    combined = (spectral_centroids + spectral_rolloff) / 2
    
    # Намиране на промени (вероятни граници на секции)
    frame_length = 2048
    hop_length = 512
    times = librosa.frames_to_time(np.arange(len(combined)), sr=sr, hop_length=hop_length)
    
    # Изчисляване на RMS енергия за по-добро разпознаване на секции
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_normalized = (rms - np.min(rms)) / (np.max(rms) - np.min(rms))
    
    return {
        'duration': duration,
        'tempo': tempo_value,
        'times': times,
        'rms': rms_normalized,
        'spectral_centroids': spectral_centroids,
        'sample_rate': sr,
        'hop_length': hop_length
    }

def estimate_sections(analysis, lyrics_structure):
    """Оценява секциите на песента въз основа на анализа и структурата на текста"""
    duration = analysis['duration']
    times = analysis['times']
    rms = analysis['rms']
    
    # Намиране на пикове в енергията (вероятни припеви)
    from scipy.signal import find_peaks
    peaks, properties = find_peaks(rms, height=0.5, distance=len(rms)//10)
    peak_times = times[peaks]
    
    # Оценка на структурата въз основа на текста
    # Имаме: Встъп, Верс 1, Припев 1, Интерлюд, Верс 2, Припев 2, Припев 3, Финал
    
    sections = []
    
    # Ако знаем приблизителната структура, можем да я използваме
    # За сега ще създадем базова структура въз основа на енергията
    
    # Намиране на точки с ниска енергия (вероятни версове или интерлюди)
    valleys, _ = find_peaks(-rms, height=-0.3, distance=len(rms)//10)
    valley_times = times[valleys]
    
    return {
        'peaks': peak_times,
        'valleys': valley_times,
        'rms_times': times,
        'rms_values': rms
    }

def create_timeline(analysis, lyrics_file):
    """Създава таймлайн с таймкодове за всеки ред от текста"""
    # Прочитане на текста
    with open(lyrics_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Филтриране на празни редове и коментари
    lyrics_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('//'):
            lyrics_lines.append(line)
    
    duration = analysis['duration']
    
    timeline = []
    current_time = 0
    
    # Дефиниране на структурата с приблизителни продължителности
    # Те ще бъдат мащабирани спрямо реалната продължителност
    structure = [
        {'type': 'intro', 'lines': 1, 'base_duration': 3.0},  # Встъп
        {'type': 'verse1', 'lines': 16, 'base_duration': 50.0},  # Верс 1 (16 реда)
        {'type': 'chorus1', 'lines': 2, 'base_duration': 8.0},  # Припев 1
        {'type': 'interlude', 'lines': 1, 'base_duration': 6.0},  # Интерлюд
        {'type': 'verse2', 'lines': 8, 'base_duration': 25.0},  # Верс 2 (8 реда)
        {'type': 'chorus2', 'lines': 2, 'base_duration': 8.0},  # Припев 2
        {'type': 'chorus3', 'lines': 2, 'base_duration': 8.0},  # Припев 3
        {'type': 'outro', 'lines': 1, 'base_duration': 5.0},  # Финал
    ]
    
    # Изчисляване на общата базова продължителност
    total_base_duration = sum(s['base_duration'] for s in structure)
    
    # Мащабиране спрямо реалната продължителност
    # Оставяме малко време за инструментални части (около 10%)
    available_duration = duration * 0.95
    scale_factor = available_duration / total_base_duration
    
    line_index = 0
    for section in structure:
        section_duration = section['base_duration'] * scale_factor
        lines_in_section = section['lines']
        time_per_line = section_duration / lines_in_section
        
        # Специални случаи за различни типове секции
        if section['type'] == 'intro':
            # Встъпът може да е по-кратък
            time_per_line = min(time_per_line, 3.0)
        elif section['type'] in ['chorus1', 'chorus2', 'chorus3']:
            # Припевите са по-енергични, може да са малко по-дълги
            time_per_line = time_per_line * 1.1
        elif section['type'] == 'interlude':
            # Интерлюдът е дълъг текст, може да е по-дълъг
            time_per_line = time_per_line * 1.2
        elif section['type'] == 'outro':
            # Финалът е повтарящ се, може да е по-дълъг
            time_per_line = time_per_line * 1.5
        
        for j in range(lines_in_section):
            if line_index < len(lyrics_lines):
                start_time = current_time
                end_time = current_time + time_per_line
                
                timeline.append({
                    'line': lyrics_lines[line_index],
                    'start': start_time,
                    'end': end_time,
                    'section': section['type']
                })
                
                current_time = end_time
                line_index += 1
    
    # Ако има остатъчно време, добавяме го към последния ред
    if current_time < duration:
        remaining = duration - current_time
        if timeline:
            timeline[-1]['end'] = duration
    
    return timeline

def main():
    audio_file = 'FakeNews.wav'
    lyrics_file = 'Lyrics.md'
    
    print("=" * 60)
    print("АНАЛИЗ НА АУДИО ФАЙЛ ЗА ТАЙМКОДОВЕ")
    print("=" * 60)
    print()
    
    # Анализ на аудио
    analysis = analyze_audio_structure(audio_file)
    
    print()
    print("=" * 60)
    print("СЪЗДАВАНЕ НА ТАЙМЛАЙН")
    print("=" * 60)
    print()
    
    # Създаване на таймлайн
    timeline = create_timeline(analysis, lyrics_file)
    
    # Записване на резултатите
    output_file = 'Timeline.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# FAKE NEWS - Таймлайн с таймкодове\n\n")
        f.write(f"**Обща продължителност:** {format_time(analysis['duration'])}\n")
        f.write(f"**Темпо (BPM):** {analysis['tempo']:.2f}\n\n")
        f.write("---\n\n")
        
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
        
        current_section = None
        for i, entry in enumerate(timeline, 1):
            start_time = format_time(entry['start'])
            end_time = format_time(entry['end'])
            duration = format_time(entry['end'] - entry['start'])
            
            # Показване на секцията само при промяна
            if entry.get('section') != current_section:
                current_section = entry.get('section')
                section_name = section_names.get(current_section, current_section)
                f.write(f"\n### {section_name.upper()}\n\n")
            
            f.write(f"## {i}. {start_time} - {end_time} ({duration})\n")
            f.write(f"**Текст:** {entry['line']}\n\n")
    
    print(f"Таймлайнът е записан в: {output_file}")
    print()
    print("Първите 10 записа:")
    print("-" * 60)
    for i, entry in enumerate(timeline[:10], 1):
        print(f"{i}. {format_time(entry['start'])} - {format_time(entry['end'])}: {entry['line'][:50]}...")
    
    print()
    print(f"Общо записи: {len(timeline)}")

if __name__ == '__main__':
    try:
        main()
    except ImportError as e:
        print(f"ГРЕШКА: Липсва необходима библиотека: {e}")
        print("\nМоля, инсталирайте необходимите библиотеки:")
        print("pip install librosa numpy scipy soundfile")
    except Exception as e:
        print(f"ГРЕШКА: {e}")
        import traceback
        traceback.print_exc()


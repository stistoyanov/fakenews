#!/usr/bin/env python3
"""
Скрипт за прецизна синхронизация на текстове с аудио
Използва анализ на вокалната активност и onset detection
"""

import librosa
import numpy as np
from scipy.signal import find_peaks
from datetime import timedelta

def format_time(seconds):
    """Форматира секунди в MM:SS.mmm формат"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def analyze_vocal_activity(audio_file):
    """Анализира вокалната активност в аудиото"""
    print(f"Зареждане и анализ на аудио: {audio_file}...")
    
    # Зареждане на аудио
    y, sr = librosa.load(audio_file, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)
    
    print(f"Продължителност: {format_time(duration)}")
    
    # Параметри за анализ
    frame_length = 2048
    hop_length = 512
    
    # 1. Onset detection - намиране на моменти, когато започва нов звук/текст
    print("Анализ на onset моменти...")
    onset_frames = librosa.onset.onset_detect(
        y=y, 
        sr=sr, 
        hop_length=hop_length,
        units='time',
        backtrack=True
    )
    
    # 2. RMS енергия - за идентифициране на вокални части
    print("Анализ на енергия...")
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    
    # 3. Spectral centroid - за разграничаване на вокал от инструменти
    print("Анализ на спектрални характеристики...")
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    
    # 4. Zero crossing rate - вокалът има по-висок ZCR
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    
    # Комбинирана метрика за вокална активност
    # Нормализиране на метриките
    rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-10)
    zcr_norm = (zcr - np.min(zcr)) / (np.max(zcr) - np.min(zcr) + 1e-10)
    centroid_norm = (spectral_centroid - np.min(spectral_centroid)) / (np.max(spectral_centroid) - np.min(spectral_centroid) + 1e-10)
    
    # Комбинирана метрика (вокалът обикновено има висока RMS, среден ZCR и среден centroid)
    vocal_activity = rms_norm * 0.5 + zcr_norm * 0.3 + (1 - centroid_norm) * 0.2
    
    # Намиране на пикове в вокалната активност (вероятни моменти, когато започва нов ред)
    peaks, properties = find_peaks(
        vocal_activity, 
        height=np.percentile(vocal_activity, 40),
        distance=int(sr / hop_length * 0.5)  # Минимум 0.5 секунди между пикове
    )
    
    peak_times = rms_times[peaks]
    
    # Филтриране на onset моменти - оставяме само тези, които са близо до вокална активност
    filtered_onsets = []
    for onset_time in onset_frames:
        # Проверяваме дали има вокална активност около този момент
        idx = np.argmin(np.abs(rms_times - onset_time))
        if idx < len(vocal_activity) and vocal_activity[idx] > np.percentile(vocal_activity, 30):
            filtered_onsets.append(onset_time)
    
    return {
        'duration': duration,
        'onset_times': filtered_onsets,
        'vocal_peaks': peak_times,
        'vocal_activity': vocal_activity,
        'rms_times': rms_times,
        'sample_rate': sr,
        'hop_length': hop_length
    }

def sync_lyrics_with_audio(analysis, lyrics_file):
    """Синхронизира текстовете с аудиото въз основа на вокалната активност"""
    # Прочитане на текста
    with open(lyrics_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Филтриране на празни редове и коментари
    lyrics_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('//'):
            lyrics_lines.append(line)
    
    print(f"\nНамерени {len(lyrics_lines)} реда текста")
    print(f"Намерени {len(analysis['onset_times'])} onset момента")
    print(f"Намерени {len(analysis['vocal_peaks'])} вокални пика")
    
    # Използване на onset моментите за синхронизация
    onset_times = sorted(analysis['onset_times'])
    vocal_peaks = sorted(analysis['vocal_peaks'])
    
    # Комбиниране на двата източника и сортиране
    all_cue_points = sorted(set(list(onset_times[:len(lyrics_lines)]) + list(vocal_peaks[:len(lyrics_lines)])))
    
    # Ако нямаме достатъчно cue точки, използваме равномерно разпределение като fallback
    if len(all_cue_points) < len(lyrics_lines):
        print(f"ВНИМАНИЕ: Намерени са само {len(all_cue_points)} cue точки за {len(lyrics_lines)} реда")
        print("Използва се хибриден подход...")
        
        # Комбинираме cue точките с равномерно разпределение
        duration = analysis['duration']
        uniform_times = np.linspace(0, duration * 0.95, len(lyrics_lines))
        
        # Смесваме двата подхода
        timeline = []
        for i, line in enumerate(lyrics_lines):
            if i < len(all_cue_points):
                start = all_cue_points[i]
            else:
                start = uniform_times[i]
            
            # Определяне на края - използваме следващия cue или средна продължителност
            if i + 1 < len(all_cue_points):
                end = all_cue_points[i + 1]
            elif i + 1 < len(uniform_times):
                end = uniform_times[i + 1]
            else:
                # Средна продължителност на ред (приблизително 4-5 секунди)
                end = start + 4.5
            
            timeline.append({
                'line': line,
                'start': start,
                'end': end
            })
    else:
        # Имаме достатъчно cue точки
        timeline = []
        for i, line in enumerate(lyrics_lines):
            start = all_cue_points[i]
            
            # Крайът е следващият cue или края на песента
            if i + 1 < len(all_cue_points):
                end = all_cue_points[i + 1]
            else:
                end = analysis['duration']
            
            timeline.append({
                'line': line,
                'start': start,
                'end': end
            })
    
    return timeline

def main():
    audio_file = 'FakeNews.wav'
    lyrics_file = 'Lyrics.md'
    output_file = 'Timeline.md'
    
    import os
    if not os.path.exists(audio_file):
        audio_file = 'FakeNews.mp3'
    
    if not os.path.exists(audio_file):
        print(f"ГРЕШКА: Не е намерен аудио файл")
        return
    
    print("=" * 60)
    print("ПРЕЦИЗНА СИНХРОНИЗАЦИЯ НА ТЕКСТОВЕ С АУДИО")
    print("=" * 60)
    print()
    
    # Анализ на вокалната активност
    analysis = analyze_vocal_activity(audio_file)
    
    print()
    print("=" * 60)
    print("СИНХРОНИЗАЦИЯ НА ТЕКСТОВЕТЕ")
    print("=" * 60)
    print()
    
    # Синхронизация
    timeline = sync_lyrics_with_audio(analysis, lyrics_file)
    
    # Определяне на секциите (за по-добра организация)
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
    
    # Определяне на секциите въз основа на позицията
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
    
    # Записване на резултатите
    print(f"Записване на таймлайн в: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# FAKE NEWS - Таймлайн с таймкодове (Прецизна синхронизация)\n\n")
        f.write(f"**Обща продължителност:** {format_time(analysis['duration'])}\n\n")
        f.write("---\n\n")
        
        current_section = None
        for i, entry in enumerate(timeline, 1):
            start_time = format_time(entry['start'])
            end_time = format_time(entry['end'])
            duration = format_time(entry['end'] - entry['start'])
            
            # Показване на секцията само при промяна
            section_type = entry.get('section', 'unknown')
            if section_type != current_section:
                current_section = section_type
                section_name = section_names.get(section_type, section_type)
                f.write(f"\n### {section_name.upper()}\n\n")
            
            f.write(f"## {i}. {start_time} - {end_time} ({duration})\n")
            f.write(f"**Текст:** {entry['line']}\n\n")
    
    print(f"\nГотово! Създадени са {len(timeline)} синхронизирани записа.")
    print("\nПървите 5 записа:")
    print("-" * 60)
    for i, entry in enumerate(timeline[:5], 1):
        print(f"{i}. {format_time(entry['start'])} - {format_time(entry['end'])}: {entry['line'][:50]}...")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ГРЕШКА: {e}")
        import traceback
        traceback.print_exc()


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_sleep_chart(history, user_id):
    dates = []
    durations = []
    
    for row in history:
        bedtime_str, _, duration, _ = row
        date_short = bedtime_str[5:10] 
        dates.append(date_short)
        durations.append(duration)  
    
    plt.figure(figsize=(8, 4))
    plt.plot(dates, durations, marker='o', color='#4A90E2', linewidth=2, label='Часы сна')
    plt.axhline(y=8.0, color='g', linestyle='--', alpha=0.6, label='Норма (8 ч)')
    
    plt.title('Анализ режима сна за неделю 📊', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Дата засыпания', fontsize=11)
    plt.ylabel('Длительность (часы)', fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.ylim(0, max(durations) + 2)
    plt.legend()
    
    filename = f"sleep_chart_{user_id}.png"
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    plt.close()
    
    return filename
import pandas as pd
from datetime import datetime
import os

def upptäck_glukosepisoder(data, villkor, min_varaktighet=pd.Timedelta(minutes=15), max_gap=pd.Timedelta(minutes=30), block_period=pd.Timedelta(hours=2)):
    episoder = []
    aktuell_episod = []
    aktuell_glukos = []
    tidsstämpel_kolumn = 2
    glukos_kolumn = 'kombinerad_glukos'

    data = data.sort_values(by=tidsstämpel_kolumn)

    for index, rad in data.iterrows():
        tidsstämpel = rad[tidsstämpel_kolumn]
        glukos = rad[glukos_kolumn]

        if pd.isna(tidsstämpel) or pd.isna(glukos):
            continue

        if villkor(glukos):
            if aktuell_episod:
                time_gap = tidsstämpel - aktuell_episod[-1]
                if time_gap <= max_gap:
                    aktuell_episod.append(tidsstämpel)
                    aktuell_glukos.append(glukos)
                else:
                    if (aktuell_episod[-1] - aktuell_episod[0]) >= min_varaktighet:
                        episoder.append((aktuell_episod[0], aktuell_episod[-1], aktuell_glukos))
                    aktuell_episod = [tidsstämpel]
                    aktuell_glukos = [glukos]
            else:
                aktuell_episod = [tidsstämpel]
                aktuell_glukos = [glukos]
        else:
            if aktuell_episod:
                if (aktuell_episod[-1] - aktuell_episod[0]) >= min_varaktighet:
                    episoder.append((aktuell_episod[0], aktuell_episod[-1], aktuell_glukos))
                aktuell_episod = []
                aktuell_glukos = []

    if aktuell_episod:
        if (aktuell_episod[-1] - aktuell_episod[0]) >= min_varaktighet:
            episoder.append((aktuell_episod[0], aktuell_episod[-1], aktuell_glukos))

    return len(episoder), episoder

def beräkna_medelduration(episoder):
    if not episoder:
        return 0
    total_varaktighet = sum([(episod[1] - episod[0]).total_seconds() / 60 for episod in episoder])
    return total_varaktighet / len(episoder)

def gruppera_episoder_efter_tidsintervall(episoder, tidsintervall):
    tidsintervall_antal = {f"{start:02d}:00-{slut:02d}:00": 0 for start, slut in tidsintervall}

    for episod in episoder:
        starttid = episod[0]
        timme = starttid.hour
        for start, slut in tidsintervall:
            if start <= timme < slut or (start > slut and (timme >= start or timme < slut)):
                tidsintervall_label = f"{start:02d}:00-{slut:02d}:00"
                tidsintervall_antal[tidsintervall_label] += 1
                break

    return tidsintervall_antal

def resampla_data(df, intervall_minuter=15):
    # Sätt tidsstämpeln som index
    df = df.set_index(2)
    
    # Kombinera glukosvärdena till en serie
    glukos_serie = df['kombinerad_glukos']
    
    # Resampla till jämna intervall och interpolera
    resamplad_serie = glukos_serie.resample(f'{intervall_minuter}T').mean()
    
    # Interpolera saknade värden (max 2 intervall = 30 min)
    resamplad_serie = resamplad_serie.interpolate(method='time', limit=2)
    
    return resamplad_serie

def öppna_fil(filepath=None, file_content=None):
    try:
        if file_content is not None:
            df = pd.read_csv(pd.io.common.StringIO(file_content.decode('utf-8')),
                            header=None,
                            engine='python',
                            skiprows=0,
                            names=range(30))
        else:
            df = pd.read_csv(filepath,
                            header=None,
                            engine='python',
                            skiprows=0,
                            names=range(30))

        df = df.drop(columns=range(14, 30), errors='ignore')
        namn = df.iloc[1, 0] if len(df) > 1 and 0 in df.columns else "Okänt"

        ny_df = df.copy()
        ny_df[4] = pd.to_numeric(ny_df[4].replace(',', '.', regex=True), errors='coerce')
        ny_df[5] = pd.to_numeric(ny_df[5].replace(',', '.', regex=True), errors='coerce')
        ny_df['kombinerad_glukos'] = ny_df[4].combine_first(ny_df[5])
        ny_df[2] = pd.to_datetime(ny_df[2], format='%d-%m-%Y %H:%M', errors='coerce')

        ny_df = ny_df[pd.notna(ny_df['kombinerad_glukos']) & pd.notna(ny_df[2])]
        ny_df = ny_df.sort_values(by=2)

        # Resampla data till 15-minuters intervall
        resamplad_data = resampla_data(ny_df, intervall_minuter=15)
        
        # Använd resamplad data för genomsnittsberäkning
        genomsnitt_glukos = resamplad_data.mean()

        max_gap = pd.Timedelta(minutes=30)
        total_tid_med_data = pd.Timedelta(0)
        total_tid = pd.Timedelta(0)
        tid_saknad_data = pd.Timedelta(0)

        for i in range(len(ny_df) - 1):
            aktuell_tid = ny_df.iloc[i, 2]
            nästa_tid = ny_df.iloc[i + 1, 2]

            if pd.notna(aktuell_tid) and pd.notna(nästa_tid):
                tidsdiff = nästa_tid - aktuell_tid
                total_tid += tidsdiff

                if tidsdiff <= max_gap:
                    total_tid_med_data += tidsdiff
                else:
                    tid_saknad_data += tidsdiff

        procent_data_tillgänglig = (total_tid_med_data / total_tid) * 100 if total_tid > pd.Timedelta(0) else 0

        nedre_gräns = 3.9
        övre_gräns = 8.0
        högre_gräns = 11.1

        mask_inom = (ny_df['kombinerad_glukos'] >= nedre_gräns) & (ny_df['kombinerad_glukos'] <= övre_gräns)
        mask_under = ny_df['kombinerad_glukos'] < nedre_gräns
        mask_8_10 = (ny_df['kombinerad_glukos'] > 8.1) & (ny_df['kombinerad_glukos'] <= 10.0)
        mask_10_11 = (ny_df['kombinerad_glukos'] >= 10.1) & (ny_df['kombinerad_glukos'] <= 11.0)
        mask_över = ny_df['kombinerad_glukos'] > högre_gräns

        tid_inom_intervall = pd.Timedelta(0)
        tid_under_intervall = pd.Timedelta(0)
        tid_8_10_intervall = pd.Timedelta(0)
        tid_10_11_intervall = pd.Timedelta(0)
        tid_över_intervall = pd.Timedelta(0)

        if len(ny_df) > 1:
            for i in range(len(ny_df) - 1):
                aktuell_tid = ny_df.iloc[i, 2]
                nästa_tid = ny_df.iloc[i + 1, 2]

                if pd.notna(aktuell_tid) and pd.notna(nästa_tid):
                    tidsdiff = nästa_tid - aktuell_tid

                    if tidsdiff <= max_gap:
                        if mask_inom.iloc[i] and mask_inom.iloc[i + 1]:
                            tid_inom_intervall += tidsdiff
                        elif mask_under.iloc[i] and mask_under.iloc[i + 1]:
                            tid_under_intervall += tidsdiff
                        elif mask_8_10.iloc[i] and mask_8_10.iloc[i + 1]:
                            tid_8_10_intervall += tidsdiff
                        elif mask_10_11.iloc[i] and mask_10_11.iloc[i + 1]:
                            tid_10_11_intervall += tidsdiff
                        elif mask_över.iloc[i] and mask_över.iloc[i + 1]:
                            tid_över_intervall += tidsdiff

        procent_inom = (tid_inom_intervall / total_tid_med_data) * 100 if total_tid_med_data > pd.Timedelta(0) else 0
        procent_under = (tid_under_intervall / total_tid_med_data) * 100 if total_tid_med_data > pd.Timedelta(0) else 0
        procent_8_10 = (tid_8_10_intervall / total_tid_med_data) * 100 if total_tid_med_data > pd.Timedelta(0) else 0
        procent_10_11 = (tid_10_11_intervall / total_tid_med_data) * 100 if total_tid_med_data > pd.Timedelta(0) else 0
        procent_över = (tid_över_intervall / total_tid_med_data) * 100 if total_tid_med_data > pd.Timedelta(0) else 0

        första_datum = ny_df[2].min().date() if not ny_df.empty and 2 in ny_df.columns else "Okänt"
        sista_datum = ny_df[2].max().date() if not ny_df.empty and 2 in ny_df.columns else "Okänt"

        eHbA1C = (genomsnitt_glukos + 2.59) / 1.59
        formaterad_eHbA1C = f"{eHbA1C:.3f}"

        fasta_mask = ny_df[2].dt.time.between(pd.Timestamp('05:50').time(), pd.Timestamp('06:10').time())
        fasta_glukos = ny_df.loc[fasta_mask, [4, 5]]
        fasta_medelvärde = round(pd.concat([fasta_glukos[4], fasta_glukos[5]]).dropna().mean(), 1)

        natt_mask = (ny_df[2].dt.hour >= 0) & (ny_df[2].dt.hour < 6)
        natt_data = ny_df.loc[natt_mask, [2, 4, 5]]
        natt_data['timme'] = natt_data[2].dt.hour
        timvisa_medelvärden = natt_data.groupby('timme')[[4, 5]].mean()
        timvisa_förändringar = timvisa_medelvärden.diff().mean(axis=1)
        genomsnittlig_förändring = timvisa_förändringar.mean()
        formaterad_förändring = f"{genomsnittlig_förändring:.3f}"

        standardavvikelse = ny_df[[4, 5]].std().mean()
        cv_procent = (standardavvikelse / genomsnitt_glukos) * 100
        formaterad_cv = f"{cv_procent:.1f}%"

        # Identifiera låga episoder
        antal_låga_episoder, låga_episoder_med_glukos = upptäck_glukosepisoder(
            ny_df,
            villkor=lambda x: x < 3.6,
            min_varaktighet=pd.Timedelta(minutes=16)
        )
        låga_episoder = [(ep[0], ep[1]) for ep in låga_episoder_med_glukos]
        
        # Identifiera höga episoder (≥10.0 mmol/L) - alla värden över 10 räknas som "höga"
        antal_höga_episoder, höga_episoder_med_glukos = upptäck_glukosepisoder(
            ny_df,
            villkor=lambda x: x >= 10.0,
            min_varaktighet=pd.Timedelta(minutes=16)
        )
        höga_episoder = [(ep[0], ep[1]) for ep in höga_episoder_med_glukos]
        
        # Sätt antalet mycket höga episoder till 0 eftersom vi inte separerar dem längre
        antal_mycket_höga_episoder = 0
        mycket_höga_episoder = []

        # Beräkna medelduration för varje typ av episod (i minuter)
        medelduration_låga = beräkna_medelduration(låga_episoder)
        medelduration_höga = beräkna_medelduration(höga_episoder)
        medelduration_mycket_höga = 0  # Ingen medelduration för mycket höga eftersom vi inte separerar dem

        tidsintervall = [(23, 5), (5, 11), (11, 17), (17, 23)]
        låga_episoder_per_tidsintervall = gruppera_episoder_efter_tidsintervall(låga_episoder, tidsintervall)
        höga_episoder_per_tidsintervall = gruppera_episoder_efter_tidsintervall(höga_episoder, tidsintervall)

        tidsintervall_rader = []
        for tidsintervall, antal in låga_episoder_per_tidsintervall.items():
            tidsintervall_rader.append({"Mått": f"Låga episoder {tidsintervall}", "Värde": antal})
        for tidsintervall, antal in höga_episoder_per_tidsintervall.items():
            tidsintervall_rader.append({"Mått": f"Höga episoder {tidsintervall}", "Värde": antal})

        total_tid_dagar = total_tid.days
        total_tid_timmar = total_tid.seconds // 3600
        total_tid_minuter = (total_tid.seconds % 3600) // 60
        formaterad_total_tid = f"{total_tid_dagar} dagar, {total_tid_timmar} timmar, {total_tid_minuter} minuter"

        # Create the main results list
        resultat = [
            {"Mått": "Genomsnittligt glukos", "Värde": genomsnitt_glukos},
            {"Mått": "eHbA1C", "Värde": formaterad_eHbA1C},
            {"Mått": "Fasteglukos (06:00 ± 10 min)", "Värde": fasta_medelvärde},
            {"Mått": "Nattlig trend (per timme)", "Värde": formaterad_förändring},
            {"Mått": "Glukosvariabilitet (%CV)", "Värde": formaterad_cv},
            {"Mått": "Procent av tid i 3.9-8.0", "Värde": f"{procent_inom:.2f}%"},
            {"Mått": "Total tid i 3.9-8.0", "Värde": str(tid_inom_intervall)},
            {"Mått": "Procent av tid under 3.9", "Värde": f"{procent_under:.2f}%"},
            {"Mått": "Total tid under 3.9", "Värde": str(tid_under_intervall)},
            {"Mått": "Procent av tid i 8.1-10.0", "Värde": f"{procent_8_10:.2f}%"},
            {"Mått": "Total tid i 8.1-10.0", "Värde": str(tid_8_10_intervall)},
            {"Mått": "Procent av tid i 10.1-11.0", "Värde": f"{procent_10_11:.2f}%"},
            {"Mått": "Total tid i 10.1-11.0", "Värde": str(tid_10_11_intervall)},
            {"Mått": "Procent av tid över 11.1 mmol/L", "Värde": f"{procent_över:.2f}%"},
            {"Mått": "Total tid över 11.1", "Värde": str(tid_över_intervall)},
            {"Mått": "Medelduration låga episoder (min)", "Värde": f"{medelduration_låga:.2f}"},
            {"Mått": "Medelduration höga episoder (≥10.0 mmol) (min)", "Värde": f"{medelduration_höga:.2f}"},
            {"Mått": "Medelduration mycket höga episoder (>11.1 mmol) (min)", "Värde": f"{medelduration_mycket_höga:.2f}"},
        ]

        # Create episode totals
        total_episod_antal = [
            {"Mått": "Totalt antal låga episoder", "Värde": antal_låga_episoder},
            {"Mått": "Totalt antal höga episoder", "Värde": antal_höga_episoder},
            {"Mått": "Totalt antal mycket höga episoder", "Värde": antal_mycket_höga_episoder},
            {"Mått": "Procent av data tillgänglig", "Värde": f"{procent_data_tillgänglig:.2f}%"},
            {"Mått": "Total tid saknad (luckor > 30 min)", "Värde": str(tid_saknad_data)},
            {"Mått": "Total tid (all data)", "Värde": formaterad_total_tid},
        ]

        # Add name and date interval at the end of the results list
        resultat.append({"Mått": "Namn", "Värde": namn})
        resultat.append({"Mått": "Datumintervall", "Värde": f"{första_datum} - {sista_datum}"})

        # Combine all results in the correct order
        resultat_df = pd.DataFrame(resultat + tidsintervall_rader + total_episod_antal)

        # Create the raw data sheet
        ny_sheet_df = ny_df[ny_df[[2, 4, 5]].notna().any(axis=1)].copy()
        ny_sheet_df['Datum'] = ny_sheet_df[2].dt.date
        ny_sheet_df['Tid'] = ny_sheet_df[2].dt.time
        ny_sheet_df['glukosvärden'] = ny_df[4].combine_first(ny_df[5]).astype(str)
        ny_sheet_df = ny_sheet_df[ny_sheet_df['glukosvärden'] != 'nan']
        ny_sheet_df = ny_sheet_df[['Datum', 'Tid', 'glukosvärden']]

        # Sanitize the name to remove any invalid characters for filenames
        sanitized_name = "".join(c for c in namn if c.isalnum() or c in (' ', '_', '-')).strip()
        output_filename = f"GlukosAnalys_{sanitized_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        if filepath:
            output_path = os.path.join(os.path.dirname(filepath), output_filename)
        else:
            output_path = output_filename

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            resultat_df.to_excel(writer, sheet_name='Resultat', index=False)
            ny_sheet_df.to_excel(writer, sheet_name='NySheet', index=False)

        return {
            'success': True,
            'excel_filename': output_path,
            'results': {
                'patient_info': {
                    'namn': namn,
                    'mätperiod': str(total_tid),
                    'täckning': f"{procent_data_tillgänglig:.1f}%",
                    'datumintervall': f"{första_datum} - {sista_datum}"
                },
                'statistik': {
                    'genomsnitt': genomsnitt_glukos,
                    'eHbA1C': formaterad_eHbA1C,
                    'cv_procent': formaterad_cv,
                    'fasteglukos': fasta_medelvärde
                },
                'tidsintervall': {
                    'inom': {'procent': procent_inom, 'tid': str(tid_inom_intervall)},
                    'under': {'procent': procent_under, 'tid': str(tid_under_intervall)},
                    '8_10': {'procent': procent_8_10, 'tid': str(tid_8_10_intervall)},
                    '10_11': {'procent': procent_10_11, 'tid': str(tid_10_11_intervall)},
                    'över': {'procent': procent_över, 'tid': str(tid_över_intervall)}
                },
                'episoder': {
                    'låga': {
                        'antal': antal_låga_episoder,
                        'lista': [{'start': ep[0].strftime('%Y-%m-%d %H:%M'), 'slut': ep[1].strftime('%Y-%m-%d %H:%M'), 'duration': f"{(ep[1] - ep[0]).total_seconds() / 60:.0f} min"} for ep in låga_episoder]
                    },
                    'höga': {
                        'antal': antal_höga_episoder,
                        'lista': [{'start': ep[0].strftime('%Y-%m-%d %H:%M'), 'slut': ep[1].strftime('%Y-%m-%d %H:%M'), 'duration': f"{(ep[1] - ep[0]).total_seconds() / 60:.0f} min"} for ep in höga_episoder]
                    },
                    'mycket_höga': {
                        'antal': antal_mycket_höga_episoder,
                        'lista': []
                    }
                },
                'medelduration': {
                    'låga': medelduration_låga,
                    'höga': medelduration_höga,
                    'mycket_höga': medelduration_mycket_höga
                }
            }
        }

    except Exception as e:
        print(f"Error in öppna_fil: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
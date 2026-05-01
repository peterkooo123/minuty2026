import streamlit as st
import pandas as pd
from datetime import date
import os
import uuid

# --- NASTAVENIA STRÁNKY ---
st.set_page_config(page_title="Minúty 2026", layout="centered")

# --- SÚBORY ---
NAMES_FILE = "Zoznam_mien.txt"
DATA_FILE = "data.csv"

# Inicializácia súborov
if not os.path.exists(NAMES_FILE):
    with open(NAMES_FILE, "w", encoding="utf-8") as f:
        f.write("Jozef\nMichal\n")

if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=["ID", "Date", "Meno", "Hodnota", "Tankovanie"])
    df_init.to_csv(DATA_FILE, index=False)

# --- POMOCNÉ FUNKCIE ---
def load_names():
    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        return sorted([line.strip() for line in f.readlines() if line.strip()])

def save_name(new_name):
    with open(NAMES_FILE, "a", encoding="utf-8") as f:
        f.write(f"{new_name}\n")

def load_data():
    df = pd.read_csv(DATA_FILE)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df['Hodnota'] = df['Hodnota'].astype(str).str.zfill(3)
    return df

def save_data(df):
    df['Hodnota'] = df['Hodnota'].astype(str).str.zfill(3)
    df.to_csv(DATA_FILE, index=False)

# --- VÝPOČET MINÚT A TRIEDENIE ---
def process_dataframe(df):
    if df.empty:
        return df
    
    # 1. KROK: Príprava zoradenia pre každý deň
    def prep_sort(group):
        vals = group['Hodnota'].astype(int)
        has_high = (vals >= 900).any()
        has_low = (vals <= 100).any()
        if has_high and has_low:
            group['SortValue'] = group['Hodnota'].apply(lambda x: int(x) + 1000 if int(x) < 500 else int(x))
        else:
            group['SortValue'] = vals
        return group

    processed_days = []
    unique_dates = sorted(df['Date'].unique())
    
    for d in unique_dates:
        day_df = df[df['Date'] == d].copy()
        day_df = prep_sort(day_df)
        processed_days.append(day_df)
    
    # 2. KROK: Spojenie a chronologické zoradenie
    full_df = pd.concat(processed_days)
    full_df = full_df.sort_values(['Date', 'SortValue'])
    
    # 3. KROK: Kontinuálny výpočet minút
    vals = full_df['Hodnota'].astype(int).tolist()
    minutes = []
    prev_val = None
    
    for v in vals:
        if prev_val is None:
            minutes.append(0)
        else:
            diff = v - prev_val
            if diff < -500:
                diff += 1000
            minutes.append(diff)
        prev_val = v
        
    full_df['Minúty'] = minutes
    
    # Zoradenie pre zobrazenie (najnovšie hore)
    return full_df.sort_values(['Date', 'SortValue'], ascending=[False, False])

# --- CALLBACK PRE ULOŽENIE A RESET ---
def save_record_callback():
    hodnota_in = st.session_state.get('input_hodnota', '')
    pridat_nove = st.session_state.get('pridat_nove_checkbox', False)
    vybrane_meno = st.session_state.get('vybrane_meno_selectbox', '')
    nove_meno = st.session_state.get('input_nove_meno', '')
    zaznam_datum = st.session_state.get('zaznam_datum', date.today())
    
    meno_na_zapis = nove_meno if pridat_nove else vybrane_meno
    
    if not hodnota_in.isdigit():
        st.session_state.action_msg = ("error", "Zadaj číselnú hodnotu (napr. 050)!")
        return
    if pridat_nove and not meno_na_zapis.strip():
        st.session_state.action_msg = ("error", "Zadaj meno nového človeka!")
        return

    names = load_names()
    if pridat_nove and meno_na_zapis not in names:
        save_name(meno_na_zapis)
        
    tank = []
    if st.session_state.get('input_t20', False): tank.append("20 L")
    if st.session_state.get('input_t40', False): tank.append("40 L")
    
    new_row = {
        "ID": str(uuid.uuid4()),
        "Date": zaznam_datum,
        "Meno": meno_na_zapis,
        "Hodnota": hodnota_in.zfill(3),
        "Tankovanie": " + ".join(tank) if tank else "-"
    }
    
    current_df = load_data()
    updated_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(updated_df)
    
    # Reset
    st.session_state.input_hodnota = ""
    st.session_state.pridat_nove_checkbox = False
    st.session_state.input_t20 = False
    st.session_state.input_t40 = False
    if 'input_nove_meno' in st.session_state:
        st.session_state.input_nove_meno = ""
        
    st.session_state.action_msg = ("success", "Záznam bol úspešne uložený!")


# --- HLAVNÁ APP ---
st.title("Minúty 2026 🏄")

# Predbežné načítanie dát pre export aj tabuľky
raw_df = load_data()
full_df_with_minutes = process_dataframe(raw_df)

# Bočný panel: Export s minútami
st.sidebar.header("Nastavenia")
if not full_df_with_minutes.empty:
    # Príprava CSV pre export (odstránime pomocné stĺpce a zoradíme)
    export_df = full_df_with_minutes.copy()
    export_df = export_df.sort_values(['Date', 'SortValue']) # Chronologicky v CSV
    export_df = export_df[['Date', 'Meno', 'Hodnota', 'Minúty', 'Tankovanie']]
    
    # utf-8-sig pridáva BOM pre správnu diakritiku v Exceli
    csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
    
    st.sidebar.download_button(
        label="Stiahnuť report (CSV s minútami)",
        data=csv_data,
        file_name=f"report_minuty_{date.today()}.csv",
        mime="text/csv"
    )

# 1. SEKCIA: PRIDAŤ ZÁZNAM
st.header("+ Pridať lyžiara")
col1, col2 = st.columns(2)
with col1:
    st.date_input("Dátum:", date.today(), key="zaznam_datum")
pridat_nove = st.checkbox("+ Pridaj meno (ak sa v zozname nenachádza)", key="pridat_nove_checkbox")

with col2:
    names = load_names()
    st.selectbox("Meno lyžiara:", options=names, disabled=pridat_nove, key="vybrane_meno_selectbox")

if pridat_nove:
    st.text_input("Zadaj nové meno", key="input_nove_meno")

st.text_input("Hodnota (posledné 3 čísla):", max_chars=3, key="input_hodnota")

st.write("Tankovanie:")
col_t1, col_t2 = st.columns(2)
col_t1.checkbox("20 L", key="input_t20")
col_t2.checkbox("40 L", key="input_t40")

st.button("Uložiť záznam", type="primary", on_click=save_record_callback)

if 'action_msg' in st.session_state:
    msg_type, msg_text = st.session_state.action_msg
    if msg_type == "error": st.error(msg_text)
    elif msg_type == "success": st.success(msg_text)
    del st.session_state.action_msg

st.divider()

# 2. SEKCIA: HISTÓRIA
st.header("História")
hist_datum = st.date_input("Vybrať deň pre históriu", date.today(), key="historia_datum")

if not full_df_with_minutes.empty:
    df_display = full_df_with_minutes[full_df_with_minutes['Date'] == hist_datum].copy()
    
    if not df_display.empty:
        df_display['Zmazať'] = False
        cols_to_show = ['ID', 'Meno', 'Hodnota', 'Minúty', 'Tankovanie', 'Zmazať']
        
        edited_df = st.data_editor(
            df_display[cols_to_show],
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None,
                "Minúty": st.column_config.NumberColumn(disabled=True),
                "Zmazať": st.column_config.CheckboxColumn("Zmazať")
            },
            key="main_editor"
        )

        if not edited_df.equals(df_display[cols_to_show]):
            if st.button("Uložiť zmeny v tabuľke"):
                to_keep = edited_df[edited_df['Zmazať'] == False][['ID', 'Meno', 'Hodnota', 'Tankovanie']]
                master_df = load_data()
                master_df = master_df[~master_df['ID'].isin(df_display['ID'])]
                to_keep['Date'] = hist_datum
                final_save = pd.concat([master_df, to_keep], ignore_index=True)
                save_data(final_save)
                st.success("Zmeny boli uložené a minúty prepočítané.")
                st.rerun()
    else:
        st.info("Žiadne záznamy pre tento deň.")

# 3. SEKCIA: SÚHRN
st.divider()
st.header("Súhrn")
if not full_df_with_minutes.empty:
    today = date.today()
    df_m = full_df_with_minutes[
        (full_df_with_minutes['Date'].apply(lambda x: x.month == today.month)) & 
        (full_df_with_minutes['Date'].apply(lambda x: x.year == today.year))
    ]
    
    sum_m = df_m.groupby('Meno')['Minúty'].sum().reset_index().rename(columns={'Minúty': 'Tento mesiac (min)'})
    sum_t = full_df_with_minutes.groupby('Meno')['Minúty'].sum().reset_index().rename(columns={'Minúty': 'Celkovo (min)'})
    
    summary = pd.merge(sum_t, sum_m, on='Meno', how='left').fillna(0)
    summary['Tento mesiac (min)'] = summary['Tento mesiac (min)'].astype(int)
    st.dataframe(summary, hide_index=True, use_container_width=True)

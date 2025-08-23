import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="Match Factor Calculator",
    page_icon="contractor.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
/* Basic styling */
.stApp {
    background-color: #f8fafc;
    transition: all 0.3s ease;
}

/* Detail cards styling */
.detail-card-digger {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(99, 102, 241, 0.08)), rgba(255,255,255,0.92);
    border: 1px solid rgba(59, 130, 246, 0.25);
    color: #0f172a; /* dark slate text for light theme */
    padding: 14px;
    border-radius: 10px;
    margin-bottom: 10px;
    font-size: 12px;
    line-height: 1.5;
    backdrop-filter: blur(6px);
    box-shadow: 0 3px 10px rgba(0,0,0,0.08);
    font-weight: 500;
    transition: all 0.3s ease;
    text-shadow: none;
}
.detail-card-digger strong { color: #111111; } /* kuatkan juga jadi hitam gelap */

/* Hauler card */
.detail-card-hauler {
    background: linear-gradient(135deg, rgba(251, 146, 60, 0.08), rgba(249, 115, 22, 0.08)), rgba(255,255,255,0.92);
    border: 1px solid rgba(251, 146, 60, 0.25);
    color: #0f172a; /* dark slate text for light theme */
    padding: 14px;
    border-radius: 10px;
    margin-bottom: 10px;
    font-size: 12px;
    line-height: 1.5;
    backdrop-filter: blur(6px);
    box-shadow: 0 3px 10px rgba(0,0,0,0.08);
    font-weight: 500;
    transition: all 0.3s ease;
    text-shadow: none;
}
.detail-card-hauler strong { color: #111111; } /* kuatkan juga jadi hitam gelap */

/* Dark theme adjustments for better contrast */
@media (prefers-color-scheme: dark) {
  .detail-card-digger,
  .detail-card-hauler {
    background: rgba(17, 24, 39, 0.88); /* near-solid dark */
    color: #f8fafc;                    /* light text */
    border-color: rgba(255, 255, 255, 0.18);
  }
  .detail-card-digger strong { color: #93c5fd; } /* blue-300 */
  .detail-card-hauler strong { color: #fdba74; } /* orange-300 */
}
</style>
""", unsafe_allow_html=True)

# Load data from CSV
@st.cache_data
def load_equipment_data():
    # Use latin-1 encoding and skip the first row (header categories)
    df = pd.read_csv('CONTOH DATA.csv', encoding='latin-1', header=1)
    
    # Extract excavator data
    excavators = {}
    trucks = {}
    materials = {}
    
    # Muat database cycle time eksternal dan normalisasi header (hilangkan BOM, spasi)
    try:
        cycle_df = pd.read_csv('data cycle time.csv', encoding='utf-8-sig')
        cycle_df.columns = (
            cycle_df.columns
            .astype(str)
            .str.strip()
            .str.replace('\ufeff', '', regex=True)
        )
        # Pastikan kolom-kolom kunci ada
        required_cols = {'Digger', 'Bucket_capacity', 'Cycle_time', 'Efficiency', 'Product_type'}
        missing = required_cols - set(cycle_df.columns)
        # Jika ada yang hilang, tetap lanjut dengan yang tersedia (fallback dilakukan di bawah)
        cycle_map = {}
        if 'Digger' in cycle_df.columns:
            for _, r in cycle_df.dropna(subset=['Digger']).iterrows():
                name = str(r['Digger']).strip()
                cycle_map[name] = {
                    'bucket_capacity': float(r['Bucket_capacity']) if 'Bucket_capacity' in cycle_df.columns and pd.notna(r['Bucket_capacity']) else None,
                    'cycle_time': float(r['Cycle_time']) if 'Cycle_time' in cycle_df.columns and pd.notna(r['Cycle_time']) else None,
                    'efficiency': float(r['Efficiency']) if 'Efficiency' in cycle_df.columns and pd.notna(r['Efficiency']) else None,
                    'product_type': str(r['Product_type']).strip() if 'Product_type' in cycle_df.columns and pd.notna(r['Product_type']) else None,
                }
        else:
            cycle_map = {}
    except Exception:
        # Jika file tidak bisa dibaca, lanjut tanpa merge
        cycle_map = {}
    
    # Process excavators (Backhoe and Shovel) - merge dengan data cycle_map bila tersedia
    excavator_rows = df[df['Product'].isin(['Backhoe', 'Shovel'])].dropna(subset=['Equipment'])
    for _, row in excavator_rows.iterrows():
        if pd.notna(row['Equipment']) and pd.notna(row['Capacity']):
            eq_name = str(row['Equipment']).strip()
            cm = cycle_map.get(eq_name, {})
            
            # Hapus penggunaan bucket_size dan kolom 'Ukuran Bucket (m_)'
            # bucket_size = float(row['Ukuran Bucket (m_)']) if 'Ukuran Bucket (m_)' in df.columns and pd.notna(row['Ukuran Bucket (m_)']) else None
            
            # Bucket capacity: prioritas dari file cycle time, fallback ke 'Capacity' dari CONTOH DATA.csv
            bucket_capacity = float(cm['bucket_capacity']) if cm.get('bucket_capacity') is not None else float(row['Capacity'])
            
            # Cycle time (detik): prioritas dari file cycle time, fallback ke 'Waktu Siklus Rata-rata (detik)' atau 25 detik
            if cm.get('cycle_time') is not None:
                cycle_time = float(cm['cycle_time'])
            elif 'Waktu Siklus Rata-rata (detik)' in df.columns and pd.notna(row['Waktu Siklus Rata-rata (detik)']):
                cycle_time = float(row['Waktu Siklus Rata-rata (detik)'])
            else:
                cycle_time = 25.0  # default aman
            
            # Efficiency: prioritas dari file cycle time, fallback 0.92
            efficiency = float(cm['efficiency']) if cm.get('efficiency') is not None else 0.92
            
            excavators[eq_name] = {
                'bucket_capacity': bucket_capacity,   # m³
                'cycle_time': cycle_time,             # detik
                'efficiency': efficiency,             # faktor efisiensi
                'product_type': row['Product']        # referensi dari CONTOH DATA.csv
            }
    
    # Process trucks (Truck and Dump Truck from your CSV data)
    truck_rows = df[df['Product'].isin(['Truck', 'Dump Truck', 'Truck Art'])].dropna(subset=['Equipment'])
    for _, row in truck_rows.iterrows():
        if pd.notna(row['Equipment']) and pd.notna(row['Capacity']):
            # Special speed settings for XDE130
            if row['Equipment'] == 'XDE130':
                speed_loaded = 20
                speed_empty = 18
            else:
                # Default speeds for all other trucks
                speed_loaded = 23
                speed_empty = 21
            
            trucks[row['Equipment']] = {
                'capacity': float(row['Capacity']),
                'speed_loaded': speed_loaded,
                'speed_empty': speed_empty,
                'product_type': row['Product']
            }
    
    # Process materials
    material_rows = df.dropna(subset=['Material'])
    for _, row in material_rows.iterrows():
        if pd.notna(row['Material']):
            bank_density = float(row['Bank (ton/m_)']) if pd.notna(row['Bank (ton/m_)']) else 2.0
            loose_density = float(row['Loose (ton/m_)']) if pd.notna(row['Loose (ton/m_)']) else 1.5
            swell_factor = float(row['Swell (Loose/Bank)']) if pd.notna(row['Swell (Loose/Bank)']) else 0.8
            
            materials[row['Material']] = {
                'density_bank': bank_density,
                'density_loose': loose_density,
                'swell_factor': swell_factor,
                'fill_factor': 0.9
            }
    
    return excavators, trucks, materials

# Load equipment data
EXCAVATORS, TRUCKS, MATERIALS = load_equipment_data()

# Job efficiency factors from CSV
JOB_EFFICIENCY = {
    'Good': 0.83,
    'Average': 0.75,
    'Rather Poor': 0.67,
    'Poor': 0.58
}

# Speed database for trucks (10-60 km/h with 1 km/h increment)
SPEED_OPTIONS = {f"{speed} km/h": speed for speed in range(10, 61)}

# Update fungsi calculate_match_factor (sekitar baris 225-235)
def calculate_match_factor(excavator_data, truck_data, material_data, haul_distance, num_trucks, job_condition='Average', reposition_time=20):
    """Calculate Match Factor based on equipment specifications from CSV data"""
    
    # Get job efficiency factor
    job_efficiency = JOB_EFFICIENCY.get(job_condition, 0.75)
    
    # Hitung Bucket Pass (sesuai formula yang diminta)
    vessel_truck_capacity_ton = truck_data['capacity']
    ff = material_data['fill_factor']
    bucket_cap_m3 = excavator_data['bucket_capacity']
    density_loose = material_data['density_loose']
    bucket_pass_calc = (vessel_truck_capacity_ton * ff) / (ff * bucket_cap_m3 * density_loose)
    bucket_pass = int(np.ceil(bucket_pass_calc))  # pembulatan ke atas
    
    # Hitung Loading Cycle Truck (dalam jam) - sinkron dengan sidebar
    loading_cycle_truck_hours = (
        ((excavator_data['cycle_time'] * bucket_pass) + reposition_time) / max(excavator_data['efficiency'], 1e-6)
    ) / 3600.0  # konversi detik ke jam
    
    # Travel times (convert to hours)
    travel_time_loaded = haul_distance / truck_data['speed_loaded']  # hours
    travel_time_empty = haul_distance / truck_data['speed_empty']    # hours
    
    # Total cycle time (hours)
    dumping_time = 1.4 / 60  # menit ke jam
    spotting_time = 0.7 / 60  # menit ke jam
    total_cycle_time = loading_cycle_truck_hours + travel_time_loaded + dumping_time + travel_time_empty + spotting_time

    # Match Factor calculation - FORMULA BARU
    match_factor = (num_trucks * loading_cycle_truck_hours) / total_cycle_time
    
    # Productivity calculation - PERBAIKAN
    truck_efficiency = truck_data.get('efficiency', 0.92)  # Tambahkan truck efficiency
    truck_productivity_tons_per_hour = (truck_data['capacity'] * truck_efficiency * job_efficiency) / total_cycle_time
    truck_productivity_bcm_per_hour = truck_productivity_tons_per_hour / material_data['density_bank']
    # Produktivitas total fleet (num_trucks * produktivitas per truck)
    total_fleet_productivity_tons = num_trucks * truck_productivity_tons_per_hour
    total_fleet_productivity_bcm = num_trucks * truck_productivity_bcm_per_hour
    
    # Hitung produktivitas digger maksimal (sama dengan yang ditampilkan di sidebar)
    digger_max_productivity_bcm = (
        excavator_data['bucket_capacity']
        * material_data['fill_factor']
        * material_data['swell_factor']
        * excavator_data['efficiency']
        * job_efficiency
    ) * (3600 / excavator_data['cycle_time'])
    digger_max_productivity_tons = digger_max_productivity_bcm * material_data['density_bank']
    
    # Batasi produktivitas total fleet agar tidak melebihi kemampuan digger
    if total_fleet_productivity_bcm > digger_max_productivity_bcm:
        total_fleet_productivity_bcm = digger_max_productivity_bcm
        total_fleet_productivity_tons = digger_max_productivity_tons
    # Jika kurang, gunakan formula sebenarnya (tidak perlu else karena sudah dihitung di atas)
    if 1.0 <= match_factor <= 1.2:
        efficiency_status = "Optimal"
        status_color = "🟢"
    elif match_factor < 1.0:
        efficiency_status = "Under-truck"
        status_color = "🔴"
    else:
        efficiency_status = "Over-truck"
        status_color = "🟡"
    
    return {
        'match_factor': match_factor,
        'productivity': total_fleet_productivity_bcm,  # Total fleet BCM/h
        'productivity_tons': total_fleet_productivity_tons,  # Total fleet ton/h
        'productivity_per_truck_bcm': truck_productivity_bcm_per_hour,  # Per truck BCM/h
        'productivity_per_truck_tons': truck_productivity_tons_per_hour,  # Per truck ton/h
        'efficiency_status': efficiency_status,
        'status_color': status_color,
        'loading_time': loading_cycle_truck_hours,  # Ganti nama untuk konsistensi
        'loading_cycle_truck': loading_cycle_truck_hours,  # Tambah key baru
        'total_cycle_time': total_cycle_time,
        'job_efficiency': job_efficiency
    }

# Tambahkan fungsi untuk menghitung jumlah truck optimal yang menghasilkan MF=1.0
def calculate_optimal_trucks_for_mf1(excavator_data, truck_data, material_data, haul_distance, job_condition='Average', reposition_time=20):
    """Calculate optimal number of trucks for Match Factor = 1.0"""
    
    # Get job efficiency factor
    job_efficiency = JOB_EFFICIENCY.get(job_condition, 0.75)
    
    # Hitung Bucket Pass
    vessel_truck_capacity_ton = truck_data['capacity']
    ff = material_data['fill_factor']
    bucket_cap_m3 = excavator_data['bucket_capacity']
    density_loose = material_data['density_loose']
    bucket_pass_calc = (vessel_truck_capacity_ton * ff) / (ff * bucket_cap_m3 * density_loose)
    bucket_pass = int(np.ceil(bucket_pass_calc))
    
    # Hitung Loading Cycle Truck (dalam jam)
    loading_cycle_truck_hours = (
        ((excavator_data['cycle_time'] * bucket_pass) + reposition_time) / max(excavator_data['efficiency'], 1e-6)
    ) / 3600.0
    
    # Travel times (convert to hours)
    travel_time_loaded = haul_distance / truck_data['speed_loaded']
    travel_time_empty = haul_distance / truck_data['speed_empty']
    
    # Total cycle time (hours)
    dumping_time = 1.4 / 60
    spotting_time = 0.7 / 60
    total_cycle_time = loading_cycle_truck_hours + travel_time_loaded + dumping_time + travel_time_empty + spotting_time
    
    # Untuk MF = 1.0: num_trucks = total_cycle_time / loading_cycle_truck_hours
    optimal_trucks = total_cycle_time / loading_cycle_truck_hours
    
    return optimal_trucks

def main():
    st.title("⚡ Match Factor Calculator")
    st.markdown("---")
    
    # Sidebar for inputs
    st.sidebar.header("📋 Parameter Input")
    
    
    # Tambahkan ikon untuk Excavator
    st.sidebar.image("svg/035-crane truck.svg", width=50)  # Ganti dengan path SVG yang sesuai
    selected_excavator = st.sidebar.selectbox(
        "Excavator:",
        list(EXCAVATORS.keys()),
        help="Pilih excavator berdasarkan data CSV"
    )
    
    # Tambahkan ikon untuk Truck
    st.sidebar.image("mining-truck.svg", width=50)  # Ganti dengan path SVG yang sesuai
    selected_truck = st.sidebar.selectbox(
        "Truck:",
        list(TRUCKS.keys()),
        help="Pilih truck berdasarkan data CSV"
    )
    st.sidebar.image("gold-panning.svg", width=50) 
    selected_material = st.sidebar.selectbox(
        "Material:",
        list(MATERIALS.keys()),
        help="Pilih material berdasarkan data CSV"
    )
    
    # Speed selection
    st.sidebar.subheader("Kecepatan Truck")
    selected_speed_loaded = st.sidebar.selectbox(
        "Kecepatan Bermuatan:",
        list(SPEED_OPTIONS.keys()),
        index=2,  # Default to 20 km/h
        help="Pilih kecepatan truck saat bermuatan"
    )
    
    selected_speed_empty = st.sidebar.selectbox(
        "Kecepatan Kosong:",
        list(SPEED_OPTIONS.keys()),
        index=4,  # Default to 30 km/h
        help="Pilih kecepatan truck saat kosong"
    )
    
    # Job condition selection
    st.sidebar.subheader("Kondisi Kerja")
    job_condition = st.sidebar.selectbox(
        "Operating Conditions:",
        list(JOB_EFFICIENCY.keys()),
        index=1,  # Default to 'Average'
        help="Kondisi operasional yang mempengaruhi efisiensi"
    )
    
    # Operational parameters
    st.sidebar.subheader("⚙️ Parameter Operasional")
    haul_distance = st.sidebar.slider(
        "Jarak Angkut (km):",
        min_value=0.5,
        max_value=15.0,
        value=3.0,
        step=0.1
    )
    
    num_trucks = st.sidebar.slider(
        "Jumlah Truck:",
        min_value=1,
        max_value=20,
        value=5,
        step=1
    )
    
    reposition_time = st.sidebar.slider(
        "Loader Reposition Time (detik):",
        min_value=0,
        max_value=60,
        value=20,
        step=1
    )
    
    # Get selected equipment data
    excavator_data = EXCAVATORS[selected_excavator]
    truck_data = TRUCKS[selected_truck].copy()  # Make a copy to modify speeds
    material_data = MATERIALS[selected_material]
    
    # Update truck speeds based on user selection
    truck_data['speed_loaded'] = SPEED_OPTIONS[selected_speed_loaded]
    truck_data['speed_empty'] = SPEED_OPTIONS[selected_speed_empty]
    
    # Calculate match factor
    result = calculate_match_factor(
        excavator_data, truck_data, material_data, haul_distance, num_trucks, job_condition, reposition_time
    )
    
    # Calculate system productivity (affected by operational parameters)
    # This should be the bottleneck productivity between excavator and truck system
    truck_volume_bcm = truck_data['capacity'] / material_data['density_bank']
    loading_time_hours = (truck_volume_bcm / excavator_data['bucket_capacity'] * excavator_data['cycle_time']) / 3600
    loading_time_hours = loading_time_hours / result['job_efficiency']  # Apply job efficiency
    
    # Calculate truck cycle time
    travel_time_loaded = haul_distance / truck_data['speed_loaded']
    travel_time_empty = haul_distance / truck_data['speed_empty']
    dumping_time = 2.0 / 60  # 2 minutes
    spotting_time = 1.0 / 60  # 1 minute
    total_truck_cycle = loading_time_hours + travel_time_loaded + dumping_time + travel_time_empty + spotting_time
    
    # System productivity is limited by the bottleneck (gunakan formula digger sesuai permintaan)
    excavator_prod_bcm = (
        excavator_data['bucket_capacity']
        * material_data['fill_factor']
        * material_data['swell_factor']
        * excavator_data['efficiency']
        * result['job_efficiency']
    ) * (3600 / excavator_data['cycle_time'])
    excavator_prod_ton = excavator_prod_bcm * material_data['density_bank']
    
    # Use excavator maximum productivity for sidebar display
    system_prod_bcm = excavator_prod_bcm  # Show digger maximum capacity
    system_prod_ton = excavator_prod_ton  # Show digger maximum capacity in tons
    truck_system_prod = (truck_volume_bcm * num_trucks) / total_truck_cycle
    
    # System productivity is the minimum of excavator and truck system capacity
    system_productivity_bcm = min(excavator_prod_bcm, truck_system_prod)
    
    # Create main layout with right sidebar
    main_col, right_sidebar_col = st.columns([3.5, 1])
    
    with main_col:
        # Main content area
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Match Factor",
                value=f"{result['match_factor']:.2f}",
                delta=f"{result['match_factor'] - 1:.2f}" if result['match_factor'] != 1 else None
            )
        
        # Update tampilan card 2 (sekitar baris 400-405)
        with col2:
            st.metric(
                label="📊 Produktivitas Total Fleet",
                value=f"{result['productivity']:.0f} BCM/h",
                delta=f"{result['productivity_tons']:.0f} ton/h"
            )
            
            # Perbaiki caption untuk menampilkan per truck
            st.caption(f"Per truck: {result['productivity_per_truck_bcm']:.0f} BCM/h ({result['productivity_per_truck_tons']:.0f} ton/h)")
            st.caption(f"Jumlah truck: {num_trucks} unit")
        
        with col3:
            # Create abbreviated status for display
            status_abbrev = {
                "Under-trucked": "Under Truck",
                "Over-trucked": "Over Truck", 
                "Optimal": "Optimal"
            }
            
            st.metric(
                label="Efficiency Status",
                value=f"{result['status_color']} {status_abbrev.get(result['efficiency_status'], result['efficiency_status'])}"
            )
        
        with col4:
            st.metric(
                label="Job Efficiency",
                value=f"{result['job_efficiency']*100:.0f}%"
            )
        
        # Equipment specifications
        st.subheader("📊 Spesifikasi Equipment")
        
        spec_col1, spec_col2, spec_col3 = st.columns(3)
        
        with spec_col1:
            st.write("**Excavator:**", selected_excavator)
            st.write(f"• Tipe: {excavator_data['product_type']}")
            st.write(f"• Kapasitas Bucket: {excavator_data['bucket_capacity']} m³")
            st.write(f"• Cycle Time: {excavator_data['cycle_time']} detik")
            st.write(f"• Kondisi Kerja: {job_condition} ({result['job_efficiency']*100:.0f}%)")
        
        with spec_col2:
            st.write("**Truck:**", selected_truck)
            st.write(f"• Tipe: {truck_data['product_type']}")
            st.write(f"• Kapasitas: {truck_data['capacity']} ton")
            st.write(f"• Kecepatan Bermuatan: {truck_data['speed_loaded']} km/h")
            st.write(f"• Kecepatan Kosong: {truck_data['speed_empty']} km/h")
        
        with spec_col3:
            st.write("**Material:**", selected_material)
            st.write(f"• Density Bank: {material_data['density_bank']} ton/m³")
            st.write(f"• Density Loose: {material_data['density_loose']} ton/m³")
            st.write(f"• Swell Factor: {material_data['swell_factor']:.2f}")
            st.write(f"• Fill Factor: {material_data['fill_factor']:.2f}")
        
        # Analysis section
        st.subheader("📈 Analisis Grafik")
        
        # Generate data for analysis
        truck_range = range(1, 21)
        distance_range = np.arange(0.5, 15.5, 0.5)
        
        # Match Factor vs Number of Trucks
        mf_data = []
        for i, trucks in enumerate(truck_range):
            result_temp = calculate_match_factor(
                excavator_data, truck_data, material_data, haul_distance, trucks, job_condition, reposition_time
            )
            mf_data.append({
                'trucks': trucks,
                'match_factor': result_temp['match_factor'],
                'productivity': result_temp['productivity'],  # Total fleet productivity
                'productivity_tons': result_temp['productivity_tons'],  # Total fleet tons
                'productivity_per_truck_bcm': result_temp['productivity_per_truck_bcm'],  # Per truck BCM
                'productivity_per_truck_tons': result_temp['productivity_per_truck_tons'],  # Per truck tons
                'status': result_temp['efficiency_status']
            })
        
        df_trucks = pd.DataFrame(mf_data)
        # Tambahkan kolom mf_diff
        df_trucks['mf_diff'] = (df_trucks['match_factor'] - 1.0).abs()
        
        # Productivity vs Distance
        prod_data = []
        for distance in distance_range:
            result_temp = calculate_match_factor(
                excavator_data, truck_data, material_data, distance, num_trucks, job_condition
            )
            # Ubah ke ton/h untuk kesesuaian dengan label chart
            productivity_ton = result_temp['productivity'] * material_data['density_bank']
            prod_data.append({
                'distance': distance,
                'match_factor': result_temp['match_factor'],
                'productivity': productivity_ton,  # Gunakan ton/h
                'status': result_temp['efficiency_status']
            })
        
        df_distance = pd.DataFrame(prod_data)
        
        # Create plots with theme-aware styling
        fig_col1, fig_col2 = st.columns(2)
        
        # Detect theme (you can use session state or user preference)
        is_dark_mode = st.sidebar.selectbox("Theme", ["Light", "Dark"], index=0) == "Dark"
        
        # Set theme-based colors
        if is_dark_mode:
            paper_bg = '#1f2937'
            plot_bg = '#374151'
            font_color = '#f8fafc'
            title_color = '#f8fafc'
        else:
            paper_bg = '#ffffff'
            plot_bg = '#f8fafc'
            font_color = '#111111'
            title_color = '#111827'
        
        with fig_col1:
            fig1 = px.line(
                df_trucks,
                x='trucks',
                y='match_factor',
                title='Match Factor vs Jumlah Truck',
                labels={'trucks': 'Jumlah Truck', 'match_factor': 'Match Factor'},
                template='plotly_white'
            )
            fig1.update_layout(
                height=400,
                margin=dict(l=40, r=40, t=40, b=40),
                paper_bgcolor=paper_bg,
                plot_bgcolor=plot_bg,
                font=dict(color=font_color, size=12),
                title=dict(font=dict(color=title_color, size=14)),
                xaxis=dict(title_font=dict(color=title_color), tickfont=dict(color=font_color)),
                yaxis=dict(title_font=dict(color=title_color), tickfont=dict(color=font_color))
            )
            fig1.add_hline(y=1.0, line_dash="dash", line_color="green", annotation_text="Optimal")
            fig1.add_hline(y=0.8, line_dash="dot", line_color="red", annotation_text="Under-trucked")
            fig1.add_hline(y=1.2, line_dash="dot", line_color="yellow", annotation_text="Over-trucked")
            # Tambahkan garis vertikal current agar sama dengan chart 2
            fig1.add_vline(x=num_trucks, line_dash="dot", line_color="blue", annotation_text="Current")
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with fig_col2:
            fig2 = px.line(
                df_distance,
                x='distance',
                y='productivity',
                title='Produktivitas vs Jarak Angkut',
                labels={'distance': 'Jarak (km)', 'productivity': 'Produktivitas (ton/h)'},
                template='plotly_white'
            )
            fig2.update_layout(
                height=400,
                margin=dict(l=40, r=40, t=40, b=40),
                paper_bgcolor=paper_bg,
                plot_bgcolor=plot_bg,
                font=dict(color=font_color, size=12),
                title=dict(font=dict(color=title_color, size=14)),
                xaxis=dict(title_font=dict(color=title_color), tickfont=dict(color=font_color)),
                yaxis=dict(title_font=dict(color=title_color), tickfont=dict(color=font_color))
            )
            fig2.add_vline(x=haul_distance, line_dash="dot", line_color="blue", annotation_text="Current")
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Right sidebar - pindahkan ke luar with main_col
        with right_sidebar_col:
            # Tambahkan pemilihan tema di sidebar kanan
            theme_choice = st.selectbox(
                "Pilih Tema",
                ["Dark", "Light"],
                key="right_theme_select"
            )
        
            # Definisikan CSS berdasarkan pilihan tema
            if theme_choice == "Dark":
                theme_css = """
                <style>
                .stApp {
                    background-color: #000000;
                    color: #ffffff;
                }
                // ... tambahkan styling dark lainnya ...
                </style>
                """
            else:
                theme_css = """
                <style>
                .stApp {
                    background-color: #f8fafc;
                    color: #111827;
                }
                // ... tambahkan styling light lainnya ...
                </style>
                """
        
            st.markdown(theme_css, unsafe_allow_html=True)
        
            st.markdown("### 📋 Detail Specs")
        
            # Pastikan system_productivity_bcm didefinisikan sebelumnya; jika tidak, hitung ulang di sini
            # Contoh: system_productivity_bcm = min(excavator_theoretical_prod, truck_system_prod)  # Dari perhitungan sebelumnya
            
            system_prod_bcm = system_productivity_bcm  # Asumsikan sudah didefinisikan; jika error, definisikan ulang
            system_prod_ton = system_prod_bcm * material_data['density_bank']

            
            # Calculate cycle times in minutes
            # Calculate cycle times in minutes (sinkronkan dengan calculate_match_factor)
            reposition_time_min = reposition_time / 60  # Konversi dari detik
            loading_time_min = result['loading_time'] * 60  # Hilangkan pembagian job_efficiency jika sudah dihitung di fungsi
            travel_time_loaded = (haul_distance / truck_data['speed_loaded']) * 60
            travel_time_empty = (haul_distance / truck_data['speed_empty']) * 60
            dumping_time = result.get('dumping_time', 1.4)  # Ambil dari result jika ada, fallback hardcoded
            maneuver_time = result.get('spotting_time', 0.7)  # Sinkronkan nama
            total_cycle_time_min = loading_time_min + travel_time_loaded + dumping_time + travel_time_empty + maneuver_time + reposition_time_min
            
            # Calculate productivities (gunakan nilai dari result untuk sinkronisasi)
            if 'excavator_prod_bcm' in result:
                excavator_theoretical_prod_bcm = result['excavator_prod_bcm']
            else:
                # Hitung ulang jika tidak ada, sinkron dengan calculate_match_factor
                excavator_theoretical_prod_bcm = (excavator_data['bucket_capacity'] * 3600 / excavator_data['cycle_time']) * excavator_data['efficiency'] * result['job_efficiency']
            
            # Di bagian Machine Hauler Section (sekitar baris 650-670)
            # Ganti perhitungan di sidebar hauler (sekitar baris 628)
            # SEBELUM (SALAH):
            # truck_prod_ton_per_unit = (truck_data['capacity'] * 60)/ total_cycle_time_min * truck_data.get('efficiency', 0.92) * result['job_efficiency']
            
            # SESUDAH (BENAR):
            truck_efficiency = truck_data.get('efficiency', 0.92)
            # Di bagian sidebar hauler (sekitar baris 632-634)
            # SEBELUM (TIDAK KONSISTEN):
            # truck_prod_ton_per_unit = (truck_data['capacity'] * truck_efficiency * result['job_efficiency']) / (total_cycle_time_min / 60)
            # truck_prod_bcm_per_unit = truck_prod_ton_per_unit / material_data['density_bank']
            
            # SESUDAH (KONSISTEN):
            # Gunakan nilai dari result untuk konsistensi
            truck_prod_ton_per_unit = result['productivity_per_truck_tons']
            truck_prod_bcm_per_unit = result['productivity_per_truck_bcm']
            
            # Total fleet productivity juga gunakan dari result
            truck_prod_ton = result['productivity_tons']
            truck_prod_bcm = result['productivity']
            
            # Atau alternatif: gunakan system_productivity_bcm dan konversi ke ton
            # truck_prod_bcm = system_productivity_bcm  # Sama dengan digger
            # truck_prod_ton = truck_prod_bcm * material_data['density_bank']
            
            # Use system productivity for display (same as col2)
            system_prod_bcm = system_productivity_bcm  # Use the calculated system productivity
            system_prod_ton = system_prod_bcm * material_data['density_bank']
            
            # Hitung Bucket Pass (sesuai formula yang diminta)
            vessel_truck_capacity_ton = truck_data['capacity']
            ff = material_data['fill_factor']
            bucket_cap_m3 = excavator_data['bucket_capacity']
            density_loose = material_data['density_loose']
            bucket_pass_calc = (vessel_truck_capacity_ton * ff) / (ff * bucket_cap_m3 * density_loose)
            bucket_pass = int(np.ceil(bucket_pass_calc))  # pembulatan ke atas
            
            # Hitung Loading Cycle Truck (menit)
            # Pada bagian perhitungan loading_cycle_truck_min (sekitar baris 636)
            loading_cycle_truck_min = (
                ((excavator_data['cycle_time'] * bucket_pass) + reposition_time) / max(excavator_data['efficiency'], 1e-6)
            ) / 60.0  # konversi ke menit untuk tampilan
            
            # Pastikan total_cycle_time_min menggunakan loading_cycle_truck_min
            total_cycle_time_min = loading_cycle_truck_min + travel_time_loaded + dumping_time + travel_time_empty + maneuver_time
            
            # Update bagian loading_time_min untuk konsistensi (sekitar baris 782)
            loading_time_min = loading_cycle_truck_min  # Gunakan nilai yang sama
            st.image("svg/035-crane truck.svg", width=80)  # Sudah ada, pastikan sesuai
            st.markdown(f"**{selected_excavator[:15]}...**" if len(selected_excavator) > 15 else f"**{selected_excavator}**")
            
            st.markdown(
                f"""
                <div class="detail-card-digger">
                    <table style="width:100%; border-collapse:collapse;">
                        <thead>
                            <tr>
                                <th style="text-align:left; padding:4px 6px;">Description</th>
                                <th style="text-align:left; padding:4px 6px;">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td style="padding:4px 6px;">Bucket</td><td style="padding:4px 6px;">{excavator_data['bucket_capacity']} m³</td></tr>
                            <tr><td style="padding:4px 6px;">Material</td><td style="padding:4px 6px;">{selected_material[:12]}...</td></tr>
                            <tr><td style="padding:4px 6px;">Density Bcm</td><td style="padding:4px 6px;">{material_data['density_bank']:.2f}</td></tr>
                            <tr><td style="padding:4px 6px;">Density Lcm</td><td style="padding:4px 6px;">{material_data['density_loose']:.2f}</td></tr>
                            <tr><td style="padding:4px 6px;">Swell Factor</td><td style="padding:4px 6px;">{material_data['swell_factor']:.2f}</td></tr>
                            <tr><td style="padding:4px 6px;">Fill Factor</td><td style="padding:4px 6px;">{material_data['fill_factor']:.2f}</td></tr>
                            <tr><td style="padding:4px 6px;">Bucket Pass</td><td style="padding:4px 6px;">{bucket_pass} pass</td></tr>
                            <tr><td style="padding:4px 6px;">Cycle Time</td><td style="padding:4px 6px;">{excavator_data['cycle_time']:.0f}s</td></tr>
                            <tr><td style="padding:4px 6px;">Operator Eff</td><td style="padding:4px 6px;">{excavator_data['efficiency']*100:.0f}%</td></tr>
                            <tr><td style="padding:4px 6px;">Job Condition</td><td style="padding:4px 6px;">{job_condition}</td></tr>
                            <tr><td style="padding:4px 6px;">Reposition Time</td><td style="padding:4px 6px;">{reposition_time:.0f} s</td></tr>
                            <tr><td style="padding:4px 6px;">Productivity (bcm/h)</td><td style="padding:4px 6px;">{system_prod_bcm:.0f}</td></tr>
                            <tr><td style="padding:4px 6px;">Productivity (ton/h)</td><td style="padding:4px 6px;">{system_prod_ton:.0f}</td></tr>
                        </tbody>
                    </table>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Machine Hauler Section
            st.image('mining-truck.svg', width=80)
            st.markdown(f"**{selected_truck[:15]}...**" if len(selected_truck) > 15 else f"**{selected_truck}**")
            
            st.markdown(
                f"""
                <div class="detail-card-hauler">
                    <table style="width:100%; border-collapse:collapse;">
                        <thead>
                            <tr>
                                <th style="text-align:left; padding:4px 6px;">Description</th>
                                <th style="text-align:left; padding:4px 6px;">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td style="padding:4px 6px;">Model</td><td style="padding:4px 6px;">{selected_truck}</td></tr>
                            <tr><td style="padding:4px 6px;">Capacity</td><td style="padding:4px 6px;">{truck_data['capacity']} ton</td></tr>
                            <tr><td style="padding:4px 6px;">Distance</td><td style="padding:4px 6px;">{haul_distance} km</td></tr>
                            <tr><td style="padding:4px 6px;">Speed Full</td><td style="padding:4px 6px;">{truck_data['speed_loaded']} km/h</td></tr>
                            <tr><td style="padding:4px 6px;">Travel 1</td><td style="padding:4px 6px;">{travel_time_loaded:.1f} min</td></tr>
                            <tr><td style="padding:4px 6px;">Speed Empty</td><td style="padding:4px 6px;">{truck_data['speed_empty']} km/h</td></tr>
                            <tr><td style="padding:4px 6px;">Travel 2</td><td style="padding:4px 6px;">{travel_time_empty:.1f} min</td></tr>
                            <tr><td style="padding:4px 6px;">Maneuver</td><td style="padding:4px 6px;">{maneuver_time:.1f} min</td></tr>
                            <tr><td style="padding:4px 6px;">Dumping</td><td style="padding:4px 6px;">{dumping_time:.1f} min</td></tr>
                            <tr><td style="padding:4px 6px;">Loading Cycle Truck</td><td style="padding:4px 6px;">{loading_cycle_truck_min:.1f} min</td></tr>
                            <tr><td style="padding:4px 6px;">Ritase</td><td style="padding:4px 6px;">{60/total_cycle_time_min:.1f} trip/h</td></tr>
                            <tr><td style="padding:4px 6px;">Cycle Time</td><td style="padding:4px 6px;">{total_cycle_time_min:.0f} min</td></tr>
                            <tr><td style="padding:4px 6px;">Operator Eff</td><td style="padding:4px 6px;">92%</td></tr>
                            <tr><td style="padding:4px 6px;">Job Condition</td><td style="padding:4px 6px;">{job_condition}</td></tr>
                            <tr><td style="padding:4px 6px;">Productivity (bcm/h)</td><td style="padding:4px 6px;">{truck_prod_bcm_per_unit:.0f}</td></tr>
                            <tr><td style="padding:4px 6px;">Productivity (ton/h)</td><td style="padding:4px 6px;">{truck_prod_ton_per_unit:.0f}</td></tr>
                        </tbody>
                    </table>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Section: Rekomendasi Optimasi + Database + Export (PASTIKAN INI MASIH DI DALAM with main_col:)
    # Perbaiki rekomendasi optimasi (sekitar baris 740-745)
    
    # Tambahkan sub judul
    st.subheader("🎯 Rekomendasi Optimal")
    
    # PERBAIKAN: Gunakan fungsi calculate_optimal_trucks_for_mf1 untuk MF tepat 1.0
    optimal_trucks_exact = calculate_optimal_trucks_for_mf1(
        excavator_data, truck_data, material_data, haul_distance, job_condition, reposition_time
    )
    
    # Gunakan ROUNDUP (pembulatan ke atas) untuk rekomendasi
    optimal_trucks_rounded = int(np.ceil(optimal_trucks_exact))
    result_optimal = calculate_match_factor(
        excavator_data, truck_data, material_data, haul_distance, optimal_trucks_rounded, job_condition, reposition_time
    )
    
    # Tampilkan rekomendasi dengan roundup
    st.success(f"🎯 **Jumlah truck optimal (MF=1.0):** {optimal_trucks_rounded} unit")
    st.info(f"📊 **Detail perhitungan:**")
    st.info(f"   • Nilai eksak: {optimal_trucks_exact:.2f} truck")
    st.info(f"   • Setelah roundup: {optimal_trucks_rounded} truck")
    st.info(f"   • MF aktual dengan {optimal_trucks_rounded} truck: {result_optimal['match_factor']:.2f}")
    
    # Produktivitas per truck dengan jumlah optimal
    st.success(f"📈 **Produktivitas per truck:** {result_optimal['productivity_per_truck_tons']:.0f} ton/h = {result_optimal['productivity_per_truck_bcm']:.0f} bcm/h")
    st.success(f"📈 **Produktivitas total fleet:** {result_optimal['productivity_tons']:.0f} ton/h = {result_optimal['productivity']:.0f} bcm/h")
    
    # Hapus baris produktivitas total fleet
 
    col1, col2 = st.columns([1,35])  # Kolom untuk ikon dan teks, sesuaikan rasio jika perlu
    with col1:
        st.image('data-mining.svg', width=35)
    with col2:
        st.subheader("Ringkasan Equipment Database")
    tab1, tab2, tab3 = st.tabs(["Excavators", "Trucks", "Materials"])
    
    with tab1:
        exc_df = pd.DataFrame.from_dict(EXCAVATORS, orient='index')
        st.dataframe(exc_df, use_container_width=True)
    
    with tab2:
        truck_df = pd.DataFrame.from_dict(TRUCKS, orient='index')
        st.dataframe(truck_df, use_container_width=True)
    
    with tab3:
        mat_df = pd.DataFrame.from_dict(MATERIALS, orient='index')
        st.dataframe(mat_df, use_container_width=True)
    
    st.subheader("💾 Export Data")
    
    if st.button("📥 Download Analysis Data (CSV)"):
        export_data = {
            'Excavator': [selected_excavator] * len(df_trucks),
            'Truck': [selected_truck] * len(df_trucks),
            'Material': [selected_material] * len(df_trucks),
            'Haul_Distance_km': [haul_distance] * len(df_trucks),
            'Job_Condition': [job_condition] * len(df_trucks),
            'Num_Trucks': df_trucks['trucks'],
            'Match_Factor': df_trucks['match_factor'],
            'Total_Fleet_Productivity_BCM': df_trucks['productivity'],
            'Total_Fleet_Productivity_Tons': df_trucks['productivity_tons'],
            'Per_Truck_Productivity_BCM': df_trucks['productivity_per_truck_bcm'],
            'Per_Truck_Productivity_Tons': df_trucks['productivity_per_truck_tons'],
            'Efficiency_Status': df_trucks['status'],
            'MF_Difference_from_Optimal': df_trucks['mf_diff']
        }
        
        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False)
        
        st.download_button(
            label="📄 Download CSV",
            data=csv,
            file_name=f"match_factor_analysis_{selected_excavator.replace(' ', '_')}_{selected_truck.replace(' ', '_')}.csv",
            mime="text/csv"
        )

    # Cycle Time Breakdown
    st.markdown("### ⏱️ Cycle Time Breakdown")
    
    # Gunakan variabel dari sidebar untuk konsistensi
    # Asumsikan travel_time_loaded, travel_time_empty sudah didefinisikan dalam menit di sidebar
    # Jika tidak, definisikan ulang:
    travel_time_loaded = (haul_distance / truck_data['speed_loaded']) * 60  # menit, sama seperti card
    travel_time_empty = (haul_distance / truck_data['speed_empty']) * 60    # menit
    dumping_time = 1.4  # menit, sinkron dengan calculate_match_factor
    maneuver_time = 0.7  # menit (spotting/maneuver), sinkron
    loading_time_min = loading_cycle_truck_min  
    reposition_time_min = reposition_time / 60  # tambahkan ini
    
    total_cycle_time_min = loading_time_min + travel_time_loaded + dumping_time + travel_time_empty + maneuver_time + reposition_time_min
    
    df_times = pd.DataFrame({
        'component': [
            'Loading Time',
            'Travel Time (Loaded)',
            'Dumping Time',
            'Travel Time (Empty)',
            'Maneuver/Spotting',
            'Reposition Time'  # tambahkan ini
        ],
        'minutes': [
            loading_time_min,
            travel_time_loaded,
            dumping_time,
            travel_time_empty,
            maneuver_time,
            reposition_time_min
        ]
    })
    df_times['percent'] = (df_times['minutes'] / total_cycle_time_min) * 100
    
    bottom_col1, bottom_col2 = st.columns(2)
    
    with bottom_col1:
        fig3 = px.bar(
            df_times.sort_values('minutes', ascending=True),
            x='minutes',
            y='component',
            orientation='h',
            title='Durasi Per Komponen (menit)',
            labels={'minutes': 'Menit', 'component': ''},
            text='minutes',
            template='plotly_white'
        )
        fig3.update_traces(marker_color='#6366F1', texttemplate='%{text:.1f}', textposition='outside')
        fig3.update_layout(
            height=380,
            margin=dict(l=40, r=40, t=40, b=40),
            paper_bgcolor=paper_bg,
            plot_bgcolor=plot_bg,
            font=dict(color=font_color, size=12),
            title=dict(font=dict(color=title_color, size=14)),
            xaxis=dict(title_font=dict(color=title_color), tickfont=dict(color=font_color), gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(title_font=dict(color=title_color), tickfont=dict(color=font_color), gridcolor='rgba(255,255,255,0.1)')
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    with bottom_col2:
            # Konversi data untuk polar chart
            N = len(df_times)
            theta = np.linspace(0.0, 2 * np.pi, N, endpoint=False)
            radii = df_times['percent'].values
            
            # Buat polar chart menggunakan plotly
            fig4 = go.Figure()
            
            # Tambahkan trace terpisah untuk setiap komponen agar legenda detail muncul
            colors = ['#6366F1', '#22C55E', '#EAB308', '#EF4444', '#A855F7', '#8B5CF6']
            for i, (comp, pct, color) in enumerate(zip(df_times['component'], df_times['percent'], colors)):
                fig4.add_trace(go.Barpolar(
                    r=[pct],
                    theta=[theta[i] * 180 / np.pi],
                    width=[360/N],
                    marker=dict(color=color, line=dict(width=0)),  # Hilangkan border
                    name=comp,  # Nama detail untuk legenda
                    hovertemplate=f'<b>{comp}</b><br>Persentase: %{{r:.1f}}%<br>Waktu: {df_times.iloc[i]["minutes"]:.1f} menit<extra></extra>',
                    showlegend=True
                ))
            
            fig4.update_layout(
                title='Kontribusi Waktu per Komponen (%)',
                height=380,
                margin=dict(l=40, r=40, t=40, b=40),
                paper_bgcolor=paper_bg,
                plot_bgcolor=plot_bg,
                font=dict(color=font_color, size=12),
                title_font=dict(color=title_color, size=14),
                showlegend=True,
                legend=dict(
                    orientation='v',
                    yanchor='middle',
                    y=0.5,
                    xanchor='left',
                    x=1.05,
                    font=dict(color=font_color, size=10),
                    bgcolor='rgba(0,0,0,0)',  # Transparent background
                    bordercolor='rgba(0,0,0,0)',  # No border
                    borderwidth=0,  # No border width
                    itemsizing='constant',  # Ukuran item legenda konsisten
                    itemwidth=30  # Lebar area warna di legenda
                ),
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(radii) * 1.1],
                        tickfont=dict(color=font_color, size=10),
                        gridcolor='rgba(128,128,128,0.3)',
                        ticksuffix='%'
                    ),
                    angularaxis=dict(
                        tickfont=dict(color=font_color, size=10),
                        gridcolor='rgba(128,128,128,0.3)',
                        linecolor='rgba(128,128,128,0.5)',
                        tickmode='array',
                        tickvals=theta * 180 / np.pi,
                        ticktext=df_times['component']
                    ),
                    bgcolor=plot_bg
                )
            )
            
            st.plotly_chart(fig4, use_container_width=True)

# Di akhir file, hanya:
if __name__ == "__main__":
    main()

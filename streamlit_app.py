import streamlit as st
import io
import re
import pandas as pd
import plotly.express as px
import numpy as np
from pypdf import PdfReader  # PyPDF2 yerine daha güncel pypdf kullanıyoruz

# Sayfa yapılandırması
st.set_page_config(page_title="Nakit Akış Analizi", layout="wide")

# Sayı formatlarını temizleme fonksiyonu
def clean_number_format(value_str):
    """Türkçe formattaki sayıları temizler ve float'a dönüştürür"""
    if not value_str:
        return 0.0
    
    # Parantez içindeki sayıları negatif olarak işaretle
    if "(" in value_str and ")" in value_str:
        value_str = "-" + value_str.replace("(", "").replace(")", "")
    
    # Temizleme işlemi
    value_str = value_str.strip()
    
    # Nokta ve virgülleri kontrol et (Türkçe formatta nokta binlik ayırıcı, virgül ondalık)
    has_dot = "." in value_str
    has_comma = "," in value_str
    
    if has_dot and has_comma:
        # Hem nokta hem virgül varsa, noktaları kaldır, virgülü noktaya çevir
        value_str = value_str.replace(".", "").replace(",", ".")
    elif has_dot:
        # Sadece nokta varsa ve birden fazla varsa, binlik ayırıcı olarak kabul et
        if value_str.count(".") > 1:
            value_str = value_str.replace(".", "")
    elif has_comma:
        # Sadece virgül varsa, ondalık ayırıcı olarak kabul et
        value_str = value_str.replace(",", ".")
    
    try:
        return float(value_str)
    except ValueError:
        return 0.0  # Dönüştürülemezse 0 döndür

def extract_text_from_pdf(file):
    """Yüklenen PDF dosyasından metni çıkarır."""
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def extract_cash_flow_data(text):
    """PDF metninden nakit akış verilerini daha kapsamlı regex ile çıkarır."""
    data = {}
    
    # Ana bölümlerin regex kalıpları - daha esnek ve kapsamlı
    patterns = {
        "A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI": [
            r'(?:A\.?\s*İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI|A\.?\s*FAALİYETLERDEN DOĞAN NAKİT AKIŞLARI|A\.?\s*ESAS FAALİYET NAKİT AKIŞLARI).*?([\-\+]?[\d\.,]+)',
        ],
        "B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI": [
            r'(?:B\.?\s*YATIRIM FAALİYETLERİNDEN(?:\s*KAYNAKLANAN)?\s*NAKİT AKIŞLARI).*?([\-\+]?[\d\.,]+)',
        ],
        "C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI": [
            r'(?:C\.?\s*FİNANSMAN FAALİYETLERİNDEN(?:\s*KAYNAKLANAN)?\s*NAKİT AKIŞLARI).*?([\-\+]?[\d\.,]+)',
        ],
        "D. YABANCI PARA ÇEVRİM FARKLARININ ETKİSİ": [
            r'(?:D\.?\s*YABANCI PARA ÇEVRİM FARKLARININ(?:\s*NAKİT VE NAKİT BENZERLERİ ÜZERİNDEKİ)?\s*ETKİSİ|KUR DEĞİŞİMİNİN ETKİLERİ).*?([\-\+]?[\d\.,]+)',
        ],
        "E. DÖNEM BAŞI NAKİT VE NAKİT BENZERLERİ": [
            r'(?:E\.?\s*DÖNEM BAŞI NAKİT VE NAKİT BENZERLERİ).*?([\-\+]?[\d\.,]+)',
        ],
        "DÖNEM SONU NAKİT VE NAKİT BENZERLERİ": [
            r'(?:DÖNEM SONU NAKİT VE NAKİT BENZERLERİ|NAKİT VE NAKİT BENZERLERİNDEKİ NET ARTIŞ).*?([\-\+]?[\d\.,]+)',
        ]
    }
    
    # Her kalıp için arama yap
    for section_name, regex_patterns in patterns.items():
        for pattern in regex_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                data[section_name] = clean_number_format(match.group(1))
                break
    
    # Alt kalemleri çıkarmak için daha kapsamlı analiz
    sub_items = {
        "A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI": {
            "Dönem Karı (Zararı)": r'(?:Dönem (?:Net )?Karı|Zararı).*?([\-\+]?[\d\.,]+)',
            "Amortisman": r'(?:Amortisman|İtfa).*?([\-\+]?[\d\.,]+)',
            "Karşılıklar ile İlgili Düzeltmeler": r'(?:Karşılıklar|Karşılık).*?([\-\+]?[\d\.,]+)',
        },
        "B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI": {
            "Duran Varlık Alımları": r'(?:Maddi|Maddi Olmayan)(?:.*)Alım(?:.*)Nakit Çıkışları.*?([\-\+]?[\d\.,]+)',
            "Duran Varlık Satışları": r'(?:Maddi|Maddi Olmayan)(?:.*)Satış(?:.*)Nakit Girişleri.*?([\-\+]?[\d\.,]+)',
        },
        "C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI": {
            "Borçlanmadan Kaynaklanan Nakit Girişleri": r'(?:Borçlanma|Borçlanmadan)(?:.*)Giriş.*?([\-\+]?[\d\.,]+)',
            "Borç Ödemelerine İlişkin Nakit Çıkışları": r'(?:Borç Ödeme|Borç Ödemelerine).*?([\-\+]?[\d\.,]+)',
        }
    }
    
    # Alt kalemleri çıkar
    for section, sub_patterns in sub_items.items():
        if section not in data:
            continue
            
        data[section + "_details"] = {}
        for sub_name, pattern in sub_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                data[section + "_details"][sub_name] = clean_number_format(match.group(1))
    
    return data

def get_date_from_filename(filename):
    """Dosya adından tarih bilgisini çıkarır"""
    # GG.AA.YYYY veya YYYY.AA.GG formatı
    date_patterns = [
        r'(\d{2})[\.-](\d{2})[\.-](\d{4})',  # GG.AA.YYYY
        r'(\d{4})[\.-](\d{2})[\.-](\d{2})',  # YYYY.AA.GG
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, filename)
        if match:
            if len(match.group(1)) == 4:  # YYYY.MM.DD formatı
                year, month, day = match.groups()
            else:  # DD.MM.YYYY formatı
                day, month, year = match.groups()
            return f"{day}.{month}.{year}"
    
    return None

# Uygulama başlığı
st.title("PDF Nakit Akış Tablosu Analizi")
st.markdown("---")

# Sol tarafta dosya yükleme
with st.sidebar:
    st.header("PDF Dosyaları")
    uploaded_files = st.file_uploader(
        "Karşılaştırmak istediğiniz PDF dosyalarını yükleyin", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.success(f"{len(uploaded_files)} PDF dosyası yüklendi")
        
    # Demo verilerle örnek gösterme
    st.markdown("---")
    show_demo = st.checkbox("Demo PDF'lerle örnek göster", value=False)

# Ana içerik
if not uploaded_files and not show_demo:
    st.info("Lütfen sol taraftan PDF dosyaları yükleyin.")
    st.markdown("""
    ### Nasıl Kullanılır?
    1. Sol taraftan bir veya daha fazla PDF dosyası yükleyin
    2. PDF'ler otomatik olarak analiz edilecektir
    3. Nakit akış verileri tabloda gösterilecektir
    4. Veriler grafiklerle görselleştirilecektir
    
    ### PDF Formatı Hakkında
    - PDF'ler, şirketlerin finansal raporlarından nakit akış tablolarını içermelidir
    - Program "İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI", "YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI" gibi bölümleri otomatik olarak tanır
    - En iyi sonuç için, PDF'in metin tabanlı olması (taranmış değil) önerilir
    """)
else:
    # PDF işleme
    cash_flow_results = {}
    
    if show_demo:
        # Demo veriler
        cash_flow_results = {
            "Şişecam 31.12.2024": {
                "A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI": 29454653.0,
                "B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI": -18830691.0,
                "C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI": 3429022.0,
                "D. YABANCI PARA ÇEVRİM FARKLARININ ETKİSİ": 1851297.0,
                "E. DÖNEM BAŞI NAKİT VE NAKİT BENZERLERİ": 54500478.0,
                "DÖNEM SONU NAKİT VE NAKİT BENZERLERİ": 53647300.0
            },
            "Şişecam 31.12.2023": {
                "A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI": 54515060.0,
                "B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI": -29758228.0,
                "C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI": -12338319.0,
                "D. YABANCI PARA ÇEVRİM FARKLARININ ETKİSİ": 5643410.0,
                "E. DÖNEM BAŞI NAKİT VE NAKİT BENZERLERİ": 60047122.0,
                "DÖNEM SONU NAKİT VE NAKİT BENZERLERİ": 54500478.0
            }
        }
    else:
        # Her PDF dosyasını işle
        with st.spinner("PDF dosyaları analiz ediliyor..."):
            for uploaded_file in uploaded_files:
                pdf_text = extract_text_from_pdf(uploaded_file)
                cash_flow_data = extract_cash_flow_data(pdf_text)
                
                if cash_flow_data:
                    # Dosya adından tarih çıkar veya dosya adını kullan
                    date_from_filename = get_date_from_filename(uploaded_file.name)
                    file_key = date_from_filename or uploaded_file.name
                    cash_flow_results[file_key] = cash_flow_data
                else:
                    st.error(f"{uploaded_file.name} dosyasından nakit akış verisi çıkarılamadı!")
    
    # Sonuçları göster - Tablo formatında
    if cash_flow_results:
        st.subheader("Nakit Akış Verileri")
        
        # Tablo oluştur
        main_sections = [
            "A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI",
            "B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI",
            "C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI",
            "D. YABANCI PARA ÇEVRİM FARKLARININ ETKİSİ",
            "E. DÖNEM BAŞI NAKİT VE NAKİT BENZERLERİ",
            "DÖNEM SONU NAKİT VE NAKİT BENZERLERİ"
        ]
        
        # Tabloyu oluştur
        table_data = []
        for section in main_sections:
            row = {"Nakit Akım Kalemi": section}
            
            for file_key, data in cash_flow_results.items():
                value = data.get(section, "-")
                if isinstance(value, (int, float)):
                    row[file_key] = f"{value:,.0f}".replace(",", ".")
                else:
                    row[file_key] = value
            
            table_data.append(row)
        
        # DataFrame oluştur ve göster
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
        
        # Grafik gösterimi
        st.subheader("Nakit Akış Grafiği")
        
        # Grafik verilerini hazırla
        graph_data = []
        for file_key, data in cash_flow_results.items():
            for section in main_sections:
                if section in data and isinstance(data[section], (int, float)):
                    graph_data.append({
                        "Dönem": file_key,
                        "Nakit Akım Kalemi": section,
                        "Değer (TL)": data[section]
                    })
        
        graph_df = pd.DataFrame(graph_data)
        
        # Grafik tipi seçimi
        chart_type = st.selectbox(
            "Grafik tipi",
            ["Çubuk Grafik", "Çizgi Grafik", "Pasta Grafik"],
            index=0
        )
        
        if chart_type == "Çubuk Grafik":
            fig = px.bar(
                graph_df, 
                x="Dönem", 
                y="Değer (TL)", 
                color="Nakit Akım Kalemi",
                barmode="group",
                title="Nakit Akış Kalemlerinin Dönemsel Karşılaştırması",
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)
            
        elif chart_type == "Çizgi Grafik":
            fig = px.line(
                graph_df, 
                x="Dönem", 
                y="Değer (TL)", 
                color="Nakit Akım Kalemi",
                markers=True,
                title="Nakit Akış Trendleri",
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)
            
        elif chart_type == "Pasta Grafik":
            # Her dönem için ayrı pasta grafik göster
            for period in graph_df["Dönem"].unique():
                period_data = graph_df[graph_df["Dönem"] == period]
                fig = px.pie(
                    period_data,
                    values="Değer (TL)",
                    names="Nakit Akım Kalemi",
                    title=f"{period} Dönemi Nakit Akış Dağılımı",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Özet analiz
        st.subheader("Dönemsel Değişim Analizi")
        
        if len(cash_flow_results) > 1:
            # Değişim tablosu oluştur
            change_data = []
            periods = list(cash_flow_results.keys())
            periods.sort()
            
            for i in range(1, len(periods)):
                prev_period = periods[i-1]
                curr_period = periods[i]
                
                for section in main_sections:
                    prev_value = cash_flow_results[prev_period].get(section, 0)
                    curr_value = cash_flow_results[curr_period].get(section, 0)
                    
                    if isinstance(prev_value, (int, float)) and isinstance(curr_value, (int, float)):
                        absolute_change = curr_value - prev_value
                        percent_change = (absolute_change / abs(prev_value) * 100) if prev_value != 0 else float('inf')
                        
                        change_data.append({
                            "Nakit Akım Kalemi": section,
                            "Dönem": f"{prev_period} → {curr_period}",
                            "Önceki Değer": f"{prev_value:,.0f}".replace(",", "."),
                            "Mevcut Değer": f"{curr_value:,.0f}".replace(",", "."),
                            "Mutlak Değişim": f"{absolute_change:,.0f}".replace(",", "."),
                            "Yüzde Değişim": f"{percent_change:.2f}%"
                        })
            
            change_df = pd.DataFrame(change_data)
            st.dataframe(change_df, use_container_width=True)
    else:
        st.warning("PDF dosyalarından veri çıkarılamadı.")

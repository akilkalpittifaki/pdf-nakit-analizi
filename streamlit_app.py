import streamlit as st
import io
import re
from pypdf import PdfReader
import pandas as pd

st.set_page_config(page_title="Nakit Akış Analizi", layout="wide")

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
    """PDF metninden nakit akış verilerini regex ile çıkarır."""
    data = {}
    
    # A Bölümü
    match = re.search(
        r'(?:A\.?\s*İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI|A\.?\s*FAALİYETLERDEN DOĞAN NAKİT AKIŞLARI).*?([\-\+]?[\d\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI"] = match.group(1)
    
    # B Bölümü
    match = re.search(
        r'(?:B\.?\s*YATIRIM FAALİYETLERİNDEN(?:\s*KAYNAKLANAN)?\s*NAKİT AKIŞLARI).*?([\-\+]?[\d\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI"] = match.group(1)
    
    # C Bölümü
    match = re.search(
        r'(?:C\.?\s*FİNANSMAN FAALİYETLERİNDEN(?:\s*KAYNAKLANAN)?\s*NAKİT AKIŞLARI).*?([\-\+]?[\d\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI"] = match.group(1)
    
    # DÖNEM SONU Bölümü
    match = re.search(
        r'(?:DÖNEM SONU NAKİT VE NAKİT BENZERLERİ).*?([\-\+]?[\d\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["DÖNEM SONU NAKİT VE NAKİT BENZERLERİ"] = match.group(1)
    
    return data

# Uygulama başlığı
st.title("PDF Nakit Akış Tablosu Analizi")
st.markdown("---")

# PDF yükleme
uploaded_files = st.file_uploader(
    "Analiz etmek istediğiniz PDF dosyalarını yükleyin", 
    type=["pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} PDF dosyası yüklendi")
    
    # PDF'leri işle
    cash_flow_results = {}
    
    with st.spinner("PDF dosyaları analiz ediliyor..."):
        for uploaded_file in uploaded_files:
            pdf_text = extract_text_from_pdf(uploaded_file)
            cash_flow_data = extract_cash_flow_data(pdf_text)
            
            if cash_flow_data:
                cash_flow_results[uploaded_file.name] = cash_flow_data
            else:
                st.error(f"{uploaded_file.name} dosyasından nakit akış verisi çıkarılamadı!")
    
    # Sonuçları göster - Tablo formatında
    if cash_flow_results:
        st.subheader("Nakit Akış Verileri")
        
        # Tablo oluştur
        table_data = []
        sections = [
            "A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI",
            "B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI",
            "C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI",
            "DÖNEM SONU NAKİT VE NAKİT BENZERLERİ"
        ]
        
        for section in sections:
            row = {"Nakit Akım Kalemi": section}
            
            for file_name, data in cash_flow_results.items():
                value = data.get(section, "-")
                row[file_name] = value
            
            table_data.append(row)
        
        # DataFrame oluştur ve göster
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
else:
    st.info("Lütfen PDF dosyaları yükleyin.")

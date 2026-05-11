from flask import Blueprint, request, jsonify, current_app, Response
import pandas as pd
import re
from datetime import datetime
from difflib import get_close_matches

# ── Coba load AI chatbot (butuh Ollama + langchain) ──────────────────────────
try:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    # from chatbot_ai import ask_ai, ask_ai_stream, init_ai_chatbot
    from chatbot_ai import ask_ai_stream, init_ai_chatbot
    _AI_AVAILABLE = True
except Exception as _ai_err:
    _AI_AVAILABLE = False
    print(f"[Chatbot] AI mode tidak tersedia ({_ai_err}). Fallback ke rule-based.")

chatbot_bp = Blueprint('chatbot', __name__)

# Kamus Bulan untuk konversi teks ke angka
MONTHS_ID = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'agu': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'des': 12
}

def shift_month(year, month, month_offset):
    """Geser bulan maju/mundur sambil menjaga perubahan tahun."""
    month_index = (year * 12 + month - 1) + month_offset
    return month_index // 12, (month_index % 12) + 1

def extract_time_and_clean_query(text):
    """Mendeteksi Tahun & Bulan, lalu menghapusnya dari kalimat pencarian"""
    year = None
    month = None
    
    text_lower = text.lower()
    now = datetime.now()

    relative_months_match = re.search(r'\b(\d+)\s+bulan\s+lalu\b', text_lower)
    relative_years_match = re.search(r'\b(\d+)\s+tahun\s+lalu\b', text_lower)
    
    # 🌟 CEK KATA KUNCI RELATIF (Bulan ini, Tahun ini)
    if relative_months_match:
        offset = int(relative_months_match.group(1))
        year, month = shift_month(now.year, now.month, -offset)
    elif re.search(r'\b(bulan lalu)\b', text_lower):
        year, month = shift_month(now.year, now.month, -1)
    elif re.search(r'\b(bulan ini|sekarang)\b', text_lower):
        month = now.month
        year = now.year
    elif relative_years_match:
        year = now.year - int(relative_years_match.group(1))
    elif re.search(r'\b(tahun lalu|tahun kemarin)\b', text_lower):
        year = now.year - 1
    elif re.search(r'\b(tahun ini)\b', text_lower):
        year = now.year
        
    # 1. Cari Tahun (4 digit, diawali 202x) jika belum terisi
    if not year:
        year_match = re.search(r'\b(202[0-9])\b', text)
        if year_match: year = int(year_match.group(1))
            
    # 2. Cari Bulan jika belum terisi
    if not month:
        for m_name, m_num in MONTHS_ID.items():
            if re.search(rf'\b{m_name}\b', text, re.IGNORECASE):
                month = m_num
                break
                
    # 3. Bersihkan kata-kata waktu dari teks
    clean_text = text
    clean_text = re.sub(r'\b\d+\s+bulan\s+lalu\b', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\b\d+\s+tahun\s+lalu\b', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\b(bulan lalu|tahun lalu|tahun kemarin|bulan ini|tahun ini)\b', '', clean_text, flags=re.IGNORECASE)
    if year and re.search(r'\b(202[0-9])\b', clean_text):
        clean_text = re.sub(r'\b(202[0-9])\b', '', clean_text)
    for m_name in MONTHS_ID.keys():
        clean_text = re.sub(rf'\b{m_name}\b', '', clean_text, flags=re.IGNORECASE)
        
    # Hapus kata keterangan waktu
    clean_text = re.sub(r'\b(pada|di|bulan|tahun|ini|itu|sekarang|kemarin|besok|hari|lalu|terakhir)\b', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text, month, year


@chatbot_bp.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """Endpoint untuk streaming response (real-time typing effect).
    
    Client akan receive Server-Sent Events (SSE) stream yang berisi
    chunks text jawaban secara bertahap, memberikan UX seperti ChatGPT.
    
    Request body:
        {
            "message": str,
            "session_id": str (optional, default="default")
        }
    
    Response: text/event-stream dengan format:
        data: <chunk_text>\\n\\n
    """
    from routes.logs import add_chat_log
    data = request.get_json()
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    # Hanya support AI mode untuk streaming
    if not _AI_AVAILABLE:
        return jsonify({
            "error": "Streaming only available in AI mode. Ollama not running."
        }), 503
    
    def generate_stream():
        import json
        full_answer = ""
        my_debug_trace = {} # Tempat menampung log dari ask_ai_stream
        
        try:
            # Panggil stream dan titipkan my_debug_trace
            for chunk in ask_ai_stream(user_message, session_id=session_id, debug_trace=my_debug_trace):
                full_answer += chunk
                # BUNGKUS DENGAN JSON AGAR NEWLINE (\n) AMAN DARI SSE PROTOCOL
                safe_chunk = json.dumps({"text": chunk})
                yield f"data: {safe_chunk}\n\n"
            
            # SIMPAN LOG KE DATABASE SETELAH SELESAI
            add_chat_log(
                question=user_message,
                session_id=session_id,
                debug_trace=my_debug_trace,
                answer=full_answer
            )
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_chunk = json.dumps({"text": f"\n\n⚠️ Error: {str(e)}"})
            yield f"data: ⚠️ Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
    
    # Return streaming response dengan MIME type text/event-stream
    # return Response(
    #     generate_stream(),
    #     mimetype='text/event-stream',
    #     headers={
    #         'Cache-Control': 'no-cache',
    #         'X-Accel-Buffering': 'no',  # Disable nginx buffering
    #         'Connection': 'keep-alive'
    #     }
    # )
    return Response(generate_stream(), mimetype='text/event-stream')


def get_item_summary(df, raw_search_query):
    # Ekstrak waktu dan bersihkan nama barang
    search_query, target_month, target_year = extract_time_and_clean_query(raw_search_query)
    
    df['itemshortdesc'] = df['itemshortdesc'].str.strip()
    
    # Pencarian Fuzzy
    mask = df['itemshortdesc'].str.contains(search_query, case=False, na=False)
    df_item = df[mask]
    
    if df_item.empty:
        import re # Pastikan import re ada di paling atas file
        
        # Pecah ketikan user menjadi array kata, misal: "ayana bamboo" -> ["ayana", "bamboo"]
        words = search_query.split()
        
        # Buat filter awal bernilai True untuk semua baris data
        mask_fuzzy = pd.Series(True, index=df.index)
        
        for w in words:
            # re.escape() akan menetralisir tanda baca seperti () atau + di dalam setiap kata
            safe_word = re.escape(w)
            mask_fuzzy = mask_fuzzy & df['itemshortdesc'].str.contains(safe_word, case=False, na=False, regex=True)
            
        df_item = df[mask_fuzzy]

    # Jika sudah melalui Step 1 dan Step 2 tapi masih kosong
    if df_item.empty:
        return None
        
    # ========================================================
    # BEST PRACTICE: DISAMBIGUATION (Jika nama item banyak/mirip)
    # ========================================================
    unique_items = df_item['itemshortdesc'].unique()
    exact_item_name = None
    
    # Cek apakah user mengetik nama spesifik yang sama persis
    exact_match = [x for x in unique_items if x.upper() == search_query.upper()]
    
    if len(exact_match) == 1:
        exact_item_name = exact_match[0]
    elif len(unique_items) == 1:
        exact_item_name = unique_items[0]
    elif 1 < len(unique_items) <= 5:
        # Jika ada 2 s/d 5 barang mirip, munculkan tombol pilihan
        options = [{"id": f"cari barang {x}", "title": x} for x in unique_items]
        return {
            "type": "choices",
            "response": f"Saya menemukan beberapa barang yang mirip dengan '<b>{search_query}</b>'. Spesifiknya barang yang mana?",
            "options": options
        }
    elif len(unique_items) > 5:
        # Bikin ingatan waktu (jika user mengetik bulan/tahun)
        time_suffix = ""
        if target_year and target_month:
            month_name = [k for k, v in MONTHS_ID.items() if v == target_month][0]
            time_suffix = f" pada bulan {month_name} {target_year}"
        elif target_year:
            time_suffix = f" pada tahun {target_year}"
            
        # Selipkan waktu ke dalam ID tersembunyi!
        options = [{"id": f"cari barang {x}{time_suffix}", "title": x} for x in unique_items]
        
        return {
            "type": "searchable_choices",
            "response": f"Ditemukan <b>{len(unique_items)}</b> barang mirip. Filter di bawah untuk mempersempit pencarian:",
            "options": options
        }

    # ========================================================
    # KALKULASI METRIK & FILTER WAKTU
    # ========================================================
    df_exact = df[df['itemshortdesc'] == exact_item_name].copy()
    
    # Terapkan Filter Waktu
    period_label = "All-time (Keseluruhan)"
    if target_year and target_month:
        df_exact = df_exact[(df_exact['aritemdate'].dt.year == target_year) & (df_exact['aritemdate'].dt.month == target_month)]
        month_name = [k for k, v in MONTHS_ID.items() if v == target_month][0].title()
        period_label = f"{month_name} {target_year}"
    elif target_year:
        df_exact = df_exact[df_exact['aritemdate'].dt.year == target_year]
        period_label = f"Tahun {target_year}"

    # Jika pada bulan/tahun tersebut barang tidak laku
    if df_exact.empty:
        return {
            "type": "text",
            "response": f"Barang <b>{exact_item_name}</b> tidak memiliki riwayat penjualan pada periode <b>{period_label}</b>."
        }
        
    total_qty = df_exact['aritemqty'].sum()
    total_omzet = df_exact['aritemdtlamt'].sum()
    
    top_cust = df_exact.groupby('custname')['aritemqty'].sum().idxmax()
    top_cust_qty = df_exact.groupby('custname')['aritemqty'].sum().max()
    
    # Build AI Report Link
    ai_report_link = f"/ai-report?type=product&id={exact_item_name}"
    
    html_response = f"""
    <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px; font-weight: bold; letter-spacing: 1px;">
            <i class="ri-bar-chart-box-line"></i> RINGKASAN ITEM
        </div>
        <div style="font-weight: 800; color: var(--accent); font-size: 14px; margin-bottom: 5px;">{exact_item_name}</div>
        <div style="font-size: 11px; color: var(--yellow); margin-bottom: 12px;"><i class="ri-calendar-event-line"></i> Periode: {period_label}</div>
        
        <div style="display: flex; gap: 10px; margin-bottom: 12px;">
            <div style="flex: 1; background: var(--card); padding: 10px; border-radius: 6px; border: 1px solid var(--border);">
                <div style="font-size: 10px; color: var(--muted);">Terjual</div>
                <div style="font-weight: bold; font-size: 13px; color: var(--text);">{total_qty:,.0f} Pcs</div>
            </div>
            <div style="flex: 1; background: var(--card); padding: 10px; border-radius: 6px; border: 1px solid var(--border);">
                <div style="font-size: 10px; color: var(--muted);">Omzet</div>
                <div style="font-weight: bold; font-size: 13px; color: var(--green);">Rp {total_omzet:,.0f}</div>
            </div>
        </div>
        
        <div style="font-size: 12px; border-top: 1px dashed var(--border); padding-top: 10px; color: var(--text);">
            <span style="color: var(--muted);">Pembeli Terbesar ({period_label}):</span><br>
            <b>{top_cust}</b> ({top_cust_qty:,.0f} Pcs)
        </div>
        
        <div style="margin-top: 15px; padding-top: 12px; border-top: 1px solid var(--border);">
            <a href="{ai_report_link}" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: 600; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: all 0.3s;" 
               onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(16, 185, 129, 0.4)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(16, 185, 129, 0.3)';">
                <i class="ri-file-chart-fill" style="font-size: 16px;"></i>
                <span>Lihat Laporan AI Lengkap</span>
                <i class="ri-arrow-right-line" style="font-size: 14px;"></i>
            </a>
        </div>
    </div>
    """
    
    return {
        "type": "html",
        "response": html_response
    }


@chatbot_bp.route("/api/chat", methods=["POST"])
def chat():
    from routes.logs import add_chat_log  # Import di sini untuk avoid circular import
    
    data = request.get_json()
    user_message = data.get("message", "").strip()
    debug_mode = data.get("debug", False)  # Optional debug flag from user
    session_id = data.get("session_id", "default")

   # ── MODE AI (LangChain + Ollama) ─────────────────────────────────────────
    if _AI_AVAILABLE:
        try:
            # 1. Siapkan struktur kamus (dict) kosong untuk diisi oleh fungsi stream
            my_debug_trace = {}
            
            # 2. Panggil fungsi stream dan berikan kamus kosong tersebut sebagai titipan
            stream_generator = ask_ai_stream(user_message, session_id=session_id, debug_trace=my_debug_trace)
            
            # 3. Kumpulkan seluruh stream menjadi string utuh
            answer = "".join(list(stream_generator))
            
            # 4. AJAIB! Sekarang my_debug_trace SUDAH TERISI PENUH dengan log Step 1, 2, dan 3!
            # Simpan log utuh tersebut ke database log Anda.
            add_chat_log(
                question=user_message,
                session_id=session_id,
                debug_trace=my_debug_trace,
                answer=answer
            )
            
            print(f"[Chatbot] MODE: AI ✅ | Q: {user_message[:60]}")
            
            if debug_mode:
                return jsonify({
                    "type": "text",
                    "response": answer,
                    "debug": my_debug_trace
                })
            else:
                return jsonify({"type": "text", "response": answer})
                
        except Exception as e:
            error_msg = str(e)
            print(f"[Chatbot] AI gagal ({error_msg}), fallback ke rule-based.")
            
            # Log error ke /logs
            add_chat_log(
                question=user_message,
                session_id=session_id,
                error=error_msg
            )
            
            # Jika timeout, return error message langsung tanpa fallback
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                timeout_response = "⏱️ AI sedang sibuk atau tidak merespons (timeout). Coba lagi dalam beberapa saat atau restart Ollama di server."
                return jsonify({
                    "type": "text",
                    "response": timeout_response
                })

    # ── MODE RULE-BASED (FALLBACK) ────────────────────────────────────────────
    print(f"[Chatbot] MODE: Rule-Based | Q: {user_message[:60]}")
    # Pastikan 'aritemdate' sudah tipe datetime
    df = current_app.config["DF_PENJUALAN"]
    if not pd.api.types.is_datetime64_any_dtype(df['aritemdate']):
        df['aritemdate'] = pd.to_datetime(df['aritemdate'])

    msg_lower = user_message.lower()
    
    # ───  INTERCEPTOR: PAGE GUIDE & HELP SYSTEM ───
    # Detect pertanyaan tentang halaman/metrics/istilah
    if re.search(r'\b(apa itu|penjelasan|fungsi|kegunaan|arti|maksud|artinya|explain|halaman|fitur)\b', msg_lower):
        from pages_guide import get_page_guide_response
        guide_response = get_page_guide_response(user_message)
        if guide_response:
            return jsonify(guide_response)
    
    # ─── TAMBAHKAN BLOK INI (INTERCEPTOR UTILITIES) ───
    # 1. Kalkulator Matematika
    if re.search(r'^(?:hitung|berapa hasil)\s+([\d\s\+\-\*\/\(\)\.]+)', msg_lower) or re.search(r'^[\d\s\+\-\*\/\(\)\.]+$', msg_lower):
        math_result = calculate_math(user_message)
        if math_result: return jsonify(math_result)

    # 2. Hitung Hari (Selisih Tanggal)
    days_match = re.search(r'(?:hitung|berapa)\s+hari\s+(?:dari|antara)\s+(.+?)\s+(?:sampai|hingga|ke|dan)\s+(.+)', msg_lower)
    if days_match:
        res = calculate_days_diff(days_match.group(1), days_match.group(2))
        if res: return jsonify(res)
    # ───────────────────────────────────────────────────

    # ─── INTERCEPTOR KOMBINASI: Hotel di kota X yang paling sering beli ───
    combo_hotel_area = re.search(r'hotel.*(?:wilayah|di|area|kota)\s+(.+?)\s+(?:yang|apa|yg).*(?:paling|sering|banyak|terbanyak)', msg_lower)
    if combo_hotel_area:
        kota_kw = combo_hotel_area.group(1).strip()
        res = get_top_customers_by_kota(df, kota_kw)
        if res: return jsonify(res)
    
    # ─── INTERCEPTOR KOMBINASI: Produk X paling laku di kota mana ───
    combo_product_area = re.search(r'(?:produk|barang|item)\s+(.+?)\s+(?:paling laku|laku|terjual|dibeli).*(?:wilayah|area|daerah|di mana|kota)', msg_lower)
    if combo_product_area:
        product_kw = combo_product_area.group(1).strip()
        res = get_top_kota_by_product(df, product_kw)
        if res: return jsonify(res)
    
    # ─── INTERCEPTOR KOMBINASI: Kota mana yang paling banyak beli produk X ───
    combo_area_product = re.search(r'(?:wilayah|area|daerah|kota).*(?:paling|banyak|sering).*(?:beli|order).*(?:produk|barang)?\s+(.+)', msg_lower)
    if combo_area_product:
        product_kw = combo_area_product.group(1).strip()
        res = get_top_kota_by_product(df, product_kw)
        if res: return jsonify(res)
        
    # ───  INTERCEPTOR: BARANG TRENDING ───
    if re.search(r'\b(trending|paling laku|hits|terlaris)\b', msg_lower):
        return jsonify(get_trending_summary(df))

    # ─── INTERCEPTOR: KOTA GEOGRAFIS ───
    area_match = re.search(r'(?:area|wilayah|geografis|penjualan di|kota)\s+(.*)', msg_lower)
    if area_match:
        kota_kw = area_match.group(1).strip()
        res = get_kota_summary(df, kota_kw)
        if res: return jsonify(res)

    # ───  INTERCEPTOR: CUSTOMER & CHURN ───
    cust_match = re.search(r'(?:hotel|customer|klien|client)\s+(.*)', msg_lower)
    if cust_match:
        cust_kw = cust_match.group(1).strip()
        res = get_customer_summary(df, cust_kw)
        if res: return jsonify(res)
        
    # ─── INTERCEPTOR: SALES / MARKETING ───
    sales_match = re.search(r'(?:sales|marketing|performa|cek sales)\s+(.*)', msg_lower)
    if sales_match:
        sales_kw = sales_match.group(1).strip()
        res = get_sales_summary(df, sales_kw)
        if res: return jsonify(res)

    # ───  CEGATAN PENCARIAN BARANG ───
    item_match = re.search(r'(?:cari|data|barang|item|penjualan)\s+(barang|item)?\s*(.*)', msg_lower)
    if item_match:
        search_keyword = item_match.group(2).strip() if item_match.group(2) else item_match.group(1).strip()
        
        if search_keyword in ['barang', 'item', 'cari', 'data', 'penjualan']:
            search_keyword = ''
        
        if search_keyword:
            summary_result = get_item_summary(df, search_keyword)
            if summary_result:
                return jsonify(summary_result)
            else:
                return jsonify({
                    "type": "text", 
                    "response": f"Maaf, saya tidak menemukan riwayat penjualan untuk barang '{search_keyword}'."
                })

    # ─── FALLBACK TUTORIAL (BEST PRACTICE) ───
    tutorial_html = """
    <div style="background: var(--bg-secondary); padding: 15px; border-radius: 8px; border: 1px dashed var(--border);">
        <div style="margin-bottom: 12px; font-weight: bold; color: var(--text); display: flex; align-items: center; gap: 6px;">
            <i class="ri-lightbulb-flash-line" style="color: var(--yellow); font-size: 16px;"></i> 
            Panduan Penggunaan
        </div>
        <div style="font-size: 12px; color: var(--muted); margin-bottom: 12px; line-height: 1.4;">
            Maaf, saya belum memahami perintah Anda. Coba gunakan salah satu format contoh berikut:
        </div>
        
        <div style="font-size: 12px; margin-bottom: 8px;">
            <b style="color: var(--orange);">🔥 Trending & Produk:</b><br>
            • "Barang apa yang lagi trending?"<br>
            • "Cari barang [Nama Barang]"
        </div>
        
        <div style="font-size: 12px; margin-bottom: 8px;">
            <b style="color: var(--green);">🏢 Customer / Hotel:</b><br>
            • "Cek customer [Nama Customer]"<br>
            • "Hotel di Bali yang paling sering beli"
        </div>
        
        <div style="font-size: 12px; margin-bottom: 8px;">
            <b style="color: var(--red);">📍 Wilayah & Sales:</b><br>
            • "Penjualan di [Nama Kota]"<br>
            • "Penjualan di Surabaya tahun ini"<br>
            • "Penjualan di Surabaya 2 bulan lalu"<br>
            • "Cek sales [Nama Sales]"
        </div>
        
        <div style="font-size: 12px;">
            <b style="color: var(--blue-400);">🧮 Kalkulator Cepat:</b><br>
            • "Hitung 1500 * 20"<br>
            • "Hitung hari dari 1 Januari sampai hari ini"
        </div>
    </div>
    """

    return jsonify({
        "type": "html",
        "response": tutorial_html
    })

# ==========================================
# 0. PERINGKAS KOTA GEOGRAFIS
# ==========================================
def get_kota_summary(df, kota_kw):
    df['kota'] = df['kota'].astype(str).str.strip()
    if 'area' in df.columns: df['area'] = df['area'].astype(str).str.strip()
        
    clean_kw, target_month, target_year = extract_time_and_clean_query(kota_kw)
    kota_kw_clean = clean_kw.lower()

    area_aliases = {
        'bali': 'bal', 'jogja' : 'yogyakarta', 'jogjakarta' : 'yogyakarta'
    }
    search_terms = [kota_kw_clean]
    if kota_kw_clean in area_aliases: search_terms.append(area_aliases[kota_kw_clean])

    # Lapis 1, 2, 3 (Pencarian String)
    if 'area' in df.columns: df_geo = df[df['kota'].str.lower().isin(search_terms) | df['area'].str.lower().isin(search_terms)]
    else: df_geo = df[df['kota'].str.lower().isin(search_terms)]

    if df_geo.empty:
        safe_kw = re.escape(kota_kw_clean)
        df_geo = df[df['kota'].str.contains(rf'\b{safe_kw}\b', case=False, na=False, regex=True)]
    
    if df_geo.empty:
        words = kota_kw_clean.split()
        mask_fuzzy = pd.Series(False, index=df.index)
        for w in words: mask_fuzzy = mask_fuzzy | df['kota'].str.contains(re.escape(w), case=False, na=False, regex=True)
        df_geo = df[mask_fuzzy]

    if df_geo.empty:
        city_candidates = df['kota'].dropna().astype(str).str.lower().unique().tolist()
        area_candidates = df['area'].dropna().astype(str).str.lower().unique().tolist() if 'area' in df.columns else []
        close_matches = get_close_matches(kota_kw_clean, city_candidates + area_candidates, n=5, cutoff=0.75)
        if close_matches:
            if 'area' in df.columns:
                df_geo = df[df['kota'].str.lower().isin(close_matches) | df['area'].str.lower().isin(close_matches)]
            else:
                df_geo = df[df['kota'].str.lower().isin(close_matches)]
    
    if df_geo.empty: return None
    
    exact_title = kota_kw_clean.title()
    if 'area' in df.columns and kota_kw_clean in area_aliases: exact_title = f"{kota_kw_clean.title()} ({area_aliases[kota_kw_clean].upper()})"
    elif not df_geo['kota'].empty: exact_title = df_geo['kota'].mode()[0].title()
    
    # 🌟 TERAPKAN FILTER WAKTU PANDAS 🌟
    period_label = "All-time (Keseluruhan)"
    if target_year and target_month:
        df_geo = df_geo[(df_geo['aritemdate'].dt.year == target_year) & (df_geo['aritemdate'].dt.month == target_month)]
        month_name = [k for k, v in MONTHS_ID.items() if v == target_month][0].title()
        period_label = f"{month_name} {target_year}"
    elif target_year:
        df_geo = df_geo[df_geo['aritemdate'].dt.year == target_year]
        period_label = f"Tahun {target_year}"

    # Cek jika kosong setelah difilter waktu
    if df_geo.empty:
        return {"type": "text", "response": f"Tidak ada data penjualan di <b>{exact_title}</b> pada <b>{period_label}</b>."}
    
    total_omzet = df_geo['aritemdtlamt'].sum()
    unique_customers = df_geo['custname'].nunique()
    
    top_customers = df_geo.groupby('custname')['aritemdtlamt'].sum().sort_values(ascending=False).head(3)
    customers_html = "".join([f"<div style='font-size: 11px; margin-bottom: 3px;'>{idx}. {cust}: <b>Rp {omzet:,.0f}</b></div>" for idx, (cust, omzet) in enumerate(top_customers.items(), 1)])
        
    top_cat = df_geo.groupby('cat1shortdesc')['aritemdtlamt'].sum().sort_values(ascending=False).head(1)
    top_cat_name = top_cat.index[0] if len(top_cat) > 0 else "N/A"
    top_cat_value = top_cat.iloc[0] if len(top_cat) > 0 else 0
    
    html = f"""
    <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px;">📍 INSIGHT KOTA</div>
        <div style="font-weight: bold; color: var(--accent); font-size: 14px; margin-bottom: 3px;">{exact_title}</div>
        <div style="font-size: 11px; color: var(--yellow); margin-bottom: 12px;"><i class="ri-calendar-event-line"></i> Periode: {period_label}</div>
        
        <div style="display: flex; gap: 10px; margin-bottom: 12px;">
            <div style="flex: 1; background: var(--card); padding: 8px; border-radius: 6px;">
                <div style="font-size: 10px; color: var(--muted);">Total Omzet</div>
                <div style="font-weight: bold; font-size: 13px; color: var(--green);">Rp {total_omzet:,.0f}</div>
            </div>
            <div style="flex: 1; background: var(--card); padding: 8px; border-radius: 6px;">
                <div style="font-size: 10px; color: var(--muted);">Total Hotel</div>
                <div style="font-weight: bold; font-size: 13px; color: var(--text);">{unique_customers}</div>
            </div>
        </div>
        <div style="margin-bottom: 10px;"><div style="font-size: 11px; color: var(--muted); margin-bottom: 5px; font-weight: bold;">Top 3 Hotel:</div>{customers_html}</div>
        <div style="border-top: 1px dashed var(--border); padding-top: 8px; font-size: 11px;">
            <span style="color: var(--muted);">Kategori Terlaris:</span><br><b>{top_cat_name}</b> (Rp {top_cat_value:,.0f})
        </div>
    </div>
    """
    return {"type": "navigation", "response": html, "nav_path": "hub-geo", "nav_query": exact_title}
# ==========================================
# 0A. TOP CUSTOMERS BY KOTA
# ==========================================
def get_top_customers_by_kota(df, kota_kw):
    df['kota'] = df['kota'].astype(str).str.strip()
    df['custname'] = df['custname'].str.strip()
    if 'area' in df.columns: df['area'] = df['area'].astype(str).str.strip()
   
    clean_kw, target_month, target_year = extract_time_and_clean_query(kota_kw)
    kota_kw_clean = clean_kw.lower()
    
    df_geo = df[df['kota'].str.lower() == kota_kw_clean]
    
    import re
    if df_geo.empty:
        safe_kw = re.escape(kota_kw_clean)
        df_geo = df[df['kota'].str.contains(rf'\b{safe_kw}\b', case=False, na=False, regex=True)]
    
    if df_geo.empty:
        words = kota_kw_clean.split()
        mask_fuzzy = pd.Series(False, index=df.index)
        for w in words: mask_fuzzy = mask_fuzzy | df['kota'].str.contains(re.escape(w), case=False, na=False, regex=True)
        df_geo = df[mask_fuzzy]

    if df_geo.empty:
        city_candidates = df['kota'].dropna().astype(str).str.lower().unique().tolist()
        close_matches = get_close_matches(kota_kw_clean, city_candidates, n=5, cutoff=0.75)
        if close_matches:
            df_geo = df[df['kota'].str.lower().isin(close_matches)]
    
    if df_geo.empty: return {"type": "text", "response": f"Maaf, tidak ditemukan penjualan di kota <b>{kota_kw_clean.title()}</b>."}
    
    exact_kota = df_geo['kota'].mode()[0]
    
    # 🌟 TERAPKAN FILTER WAKTU PANDAS 🌟
    period_label = "All-time (Keseluruhan)"
    if target_year and target_month:
        df_geo = df_geo[(df_geo['aritemdate'].dt.year == target_year) & (df_geo['aritemdate'].dt.month == target_month)]
        period_label = f"{[k for k, v in MONTHS_ID.items() if v == target_month][0].title()} {target_year}"
    elif target_year:
        df_geo = df_geo[df_geo['aritemdate'].dt.year == target_year]
        period_label = f"Tahun {target_year}"

    if df_geo.empty: return {"type": "text", "response": f"Tidak ada riwayat penjualan di <b>{exact_kota.title()}</b> pada periode <b>{period_label}</b>."}
    
    top_customers = df_geo.groupby('custname').agg({'aritemdtlamt': 'sum', 'aritemqty': 'sum', 'aritemdate': 'count'}).rename(columns={'aritemdate': 'total_transaksi'}).sort_values('aritemdtlamt', ascending=False).head(5)
    
    customers_html = ""
    for idx, (cust, row) in enumerate(top_customers.iterrows(), 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        customers_html += f"<div style='background: var(--card); padding: 8px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid {'var(--yellow)' if idx == 1 else 'var(--border)'}'><div style='font-size: 12px; font-weight: bold; color: var(--text); margin-bottom: 3px;'>{medal} {cust}</div><div style='font-size: 10px; color: var(--muted);'>Omzet: <span style='color: var(--green); font-weight: bold;'>Rp {row['aritemdtlamt']:,.0f}</span> • {row['total_transaksi']}x order</div></div>"
    
    html = f"""
    <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px;">🏆 TOP HOTEL DI KOTA</div>
        <div style="font-weight: bold; color: var(--accent); font-size: 14px; margin-bottom: 3px;">{exact_kota.title()}</div>
        <div style="font-size: 11px; color: var(--yellow); margin-bottom: 10px;"><i class="ri-calendar-event-line"></i> Periode: {period_label}</div>
        <div style="margin-bottom: 10px;">{customers_html}</div>
    </div>
    """
    return {"type": "html", "response": html}

# ==========================================
# 0B. TOP AREAS BY PRODUCT
# ==========================================
def get_top_kota_by_product(df, product_kw):
    df['itemshortdesc'] = df['itemshortdesc'].str.strip()
    df['kota'] = df['kota'].astype(str).str.strip()
    
    # 🌟 PASANG MESIN CUCI DI SINI 🌟
    clean_kw, target_month, target_year = extract_time_and_clean_query(product_kw)
    
    mask = df['itemshortdesc'].str.contains(clean_kw, case=False, na=False, regex=False)
    df_product = df[mask]
    
    if df_product.empty:
        import re
        words = clean_kw.split()
        mask_fuzzy = pd.Series(True, index=df.index)
        for w in words: mask_fuzzy = mask_fuzzy & df['itemshortdesc'].str.contains(re.escape(w), case=False, na=False, regex=True)
        df_product = df[mask_fuzzy]
    
    if df_product.empty: return {"type": "text", "response": f"Maaf, tidak ditemukan penjualan untuk produk <b>{clean_kw}</b>."}
    
    unique_items = df_product['itemshortdesc'].unique()
    if len(unique_items) > 5: return {"type": "text", "response": f"Ditemukan <b>{len(unique_items)}</b> produk mirip. Mohon lebih spesifik."}
    elif len(unique_items) > 1: return {"type": "choices", "response": "Produk yang mana?", "options": [{"id": f"kota paling banyak beli {x}", "title": x} for x in unique_items]}
    
    exact_product = unique_items[0]
    df_exact = df_product[df_product['itemshortdesc'] == exact_product].copy()
    
    # 🌟 TERAPKAN FILTER WAKTU PANDAS 🌟
    period_label = "All-time (Keseluruhan)"
    if target_year and target_month:
        df_exact = df_exact[(df_exact['aritemdate'].dt.year == target_year) & (df_exact['aritemdate'].dt.month == target_month)]
        period_label = f"{[k for k, v in MONTHS_ID.items() if v == target_month][0].title()} {target_year}"
    elif target_year:
        df_exact = df_exact[df_exact['aritemdate'].dt.year == target_year]
        period_label = f"Tahun {target_year}"

    if df_exact.empty: return {"type": "text", "response": f"Produk <b>{exact_product}</b> tidak terjual pada periode <b>{period_label}</b>."}
    
    top_cities = df_exact.groupby('kota').agg({'aritemdtlamt': 'sum', 'aritemqty': 'sum', 'custname': 'nunique'}).rename(columns={'custname': 'total_customer'}).sort_values('aritemqty', ascending=False).head(5)
    
    cities_html = ""
    for idx, (city, row) in enumerate(top_cities.iterrows(), 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        cities_html += f"<div style='background: var(--card); padding: 8px; border-radius: 6px; margin-bottom: 6px;'><div style='font-size: 12px; font-weight: bold; color: var(--text);'>{medal} {city}</div><div style='font-size: 10px; color: var(--muted);'>Terjual: <span style='color: var(--green); font-weight: bold;'>{row['aritemqty']:,.0f} Pcs</span> • {row['total_customer']} Hotel</div></div>"
    
    html = f"""
    <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px;">📍 KOTA PEMBELI TERBANYAK</div>
        <div style="font-weight: bold; color: var(--accent); font-size: 14px; margin-bottom: 3px;">{exact_product}</div>
        <div style="font-size: 11px; color: var(--yellow); margin-bottom: 12px;"><i class="ri-calendar-event-line"></i> Periode: {period_label}</div>
        <div style="margin-bottom: 12px;">{cities_html}</div>
    </div>
    """
    return {"type": "html", "response": html}
# ==========================================
# 1. PERINGKAS CUSTOMER & CHURN (HOTEL PASIF)
# ==========================================
def get_customer_summary(df, cust_name):
    df['custname'] = df['custname'].str.strip()
    
    # Step 1: Exact / Partial Match (Tahan Tanda Baca)
    mask = df['custname'].str.contains(cust_name, case=False, na=False, regex=False)
    df_cust = df[mask]
    
    # Step 2: Fuzzy Match (Jika nama terbalik/acak)
    if df_cust.empty:
        import re
        words = cust_name.split()
        mask_fuzzy = pd.Series(True, index=df.index)
        for w in words:
            mask_fuzzy = mask_fuzzy & df['custname'].str.contains(re.escape(w), case=False, na=False, regex=True)
        df_cust = df[mask_fuzzy]

    if df_cust.empty:
        return None
        
    # === DISAMBIGUATION (PILIHAN GANDA) ===
    unique_custs = df_cust['custname'].unique()
    exact_cust = None
    
    exact_match = [x for x in unique_custs if x.upper() == cust_name.upper()]
    
    if len(exact_match) == 1:
        exact_cust = exact_match[0]
    elif len(unique_custs) == 1:
        exact_cust = unique_custs[0]
    elif len(unique_custs) > 1:
        options = [{"id": f"cek customer {x}", "title": x} for x in unique_custs]
        return {
            "type": "searchable_choices",
            "response": f"Ditemukan <b>{len(unique_custs)}</b> customer mirip. Filter di bawah:",
            "options": options
        }

    # === KALKULASI CHURN & OMZET ===
    df_exact = df[df['custname'] == exact_cust].copy()
    total_omzet = df_exact['aritemdtlamt'].sum()
    
    last_order = df_exact['aritemdate'].max()
    now = df['aritemdate'].max()
    days_inactive = (now - last_order).days
    
    status = "🟢 AKTIF"
    if days_inactive > 90:
        status = f"🔴 PASIF (Sudah {days_inactive} hari tidak order)"
    elif days_inactive > 60:
        status = f"🟡 WARNING ({days_inactive} hari tidak order)"
        
    # Build AI Report Link
    ai_report_link = f"/ai-report?type=customer&id={exact_cust}"
    
    html = f"""
    <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px;">🏢 INSIGHT CUSTOMER</div>
        <div style="font-weight: bold; color: var(--accent); font-size: 14px; margin-bottom: 10px;">{exact_cust}</div>
        <div style="font-size: 12px; margin-bottom: 5px;">Total Omzet: <b>Rp {total_omzet:,.0f}</b></div>
        <div style="font-size: 12px; margin-bottom: 5px;">Transaksi Terakhir: <b>{last_order.strftime('%d %b %Y')}</b></div>
        <div style="font-size: 12px; padding: 5px; background: var(--card); border-radius: 4px; margin-top: 10px;">
            Status: <b>{status}</b>
        </div>
        <div style="margin-top: 15px; padding-top: 12px; border-top: 1px solid var(--border);">
            <a href="{ai_report_link}" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: 600; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: all 0.3s;" 
               onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(16, 185, 129, 0.4)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(16, 185, 129, 0.3)';">
                <i class="ri-file-chart-fill" style="font-size: 16px;"></i>
                <span>Lihat Laporan AI Lengkap</span>
                <i class="ri-arrow-right-line" style="font-size: 14px;"></i>
            </a>
        </div>
    </div>
    """
    return {"type": "html", "response": html}

# ==========================================
# 4. PERINGKAS PERFORMA SALES
# ==========================================
def get_sales_summary(df, sales_name):
    # Pastikan kolom salesname bersih dari spasi
    df['salesname'] = df['salesname'].astype(str).str.strip()
    
    # Step 1: Exact / Partial Match (Tahan Tanda Baca)
    mask = df['salesname'].str.contains(sales_name, case=False, na=False, regex=False)
    df_sales = df[mask]
    
    # Step 2: Fuzzy Match (Jika nama terbalik/acak)
    if df_sales.empty:
        import re
        words = sales_name.split()
        mask_fuzzy = pd.Series(True, index=df.index)
        for w in words:
            mask_fuzzy = mask_fuzzy & df['salesname'].str.contains(re.escape(w), case=False, na=False, regex=True)
        df_sales = df[mask_fuzzy]

    if df_sales.empty:
        return None
        
    # === DISAMBIGUATION (PILIHAN GANDA JIKA NAMA MIRIP) ===
    unique_sales = df_sales['salesname'].unique()
    exact_sales = None
    
    exact_match = [x for x in unique_sales if x.upper() == sales_name.upper()]
    
    if len(exact_match) == 1:
        exact_sales = exact_match[0]
    elif len(unique_sales) == 1:
        exact_sales = unique_sales[0]
    elif len(unique_sales) > 1:
        # Tampilkan searchable dropdown layaknya pencarian item
        options = [{"id": f"cek sales {x}", "title": x} for x in unique_sales]
        return {
            "type": "searchable_choices",
            "response": f"Ditemukan <b>{len(unique_sales)}</b> nama sales mirip. Filter di bawah:",
            "options": options
        }

    # === KALKULASI PERFORMA SALES ===
    df_exact = df[df['salesname'] == exact_sales].copy()
    
    total_omzet = df_exact['aritemdtlamt'].sum()
    total_tx = len(df_exact)
    total_cust = df_exact['custname'].nunique()
    
    # Hitung void/negatif untuk mencari "Clean Omzet"
    void_omzet = abs(df_exact[df_exact['aritemqty'] < 0]['aritemdtlamt'].sum())
    clean_omzet = total_omzet - void_omzet
    
    # Cari customer pegangan terbesar dari sales ini
    top_cust = df_exact.groupby('custname')['aritemdtlamt'].sum().idxmax()
    
    # Build AI Report Link
    ai_report_link = f"/ai-report?type=sales&id={exact_sales}"
    
    html = f"""
    <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px; font-weight: bold; letter-spacing: 1px;">
            <i class="ri-user-star-line"></i> PERFORMA SALES
        </div>
        <div style="font-weight: 800; color: var(--accent); font-size: 15px; margin-bottom: 12px;">{exact_sales.upper()}</div>
        
        <div style="display: flex; gap: 10px; margin-bottom: 12px;">
            <div style="flex: 1; background: var(--card); padding: 10px; border-radius: 6px; border: 1px solid var(--border);">
                <div style="font-size: 10px; color: var(--muted);">Total Transaksi</div>
                <div style="font-weight: bold; font-size: 13px; color: var(--text);">{total_tx:,.0f}</div>
            </div>
            <div style="flex: 1; background: var(--card); padding: 10px; border-radius: 6px; border: 1px solid var(--border);">
                <div style="font-size: 10px; color: var(--muted);">Clean Omzet</div>
                <div style="font-weight: bold; font-size: 13px; color: var(--green);">Rp {clean_omzet:,.0f}</div>
            </div>
        </div>
        
        <div style="font-size: 12px; border-top: 1px dashed var(--border); padding-top: 10px; color: var(--text);">
            <span style="color: var(--muted);">Customer Terbesar:</span><br>
            <b>{top_cust}</b> (dari {total_cust} customer)
        </div>
        
        <div style="margin-top: 15px; padding-top: 12px; border-top: 1px solid var(--border);">
            <a href="{ai_report_link}" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: 600; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: all 0.3s;" 
               onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(16, 185, 129, 0.4)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(16, 185, 129, 0.3)';">
                <i class="ri-file-chart-fill" style="font-size: 16px;"></i>
                <span>Lihat Laporan AI Lengkap</span>
                <i class="ri-arrow-right-line" style="font-size: 14px;"></i>
            </a>
        </div>
    </div>
    """
    
    return {
        "type": "html",
        "response": html
    }

# ==========================================
# 7. PERINGKAS BARANG TRENDING
# ==========================================
def get_trending_summary(df):
    # Ambil data 1 bulan terakhir
    now = df['aritemdate'].max()
    last_month = now - pd.Timedelta(days=30)
    df_recent = df[df['aritemdate'] >= last_month]
    
    top_items = df_recent.groupby('itemshortdesc')['aritemqty'].sum().nlargest(3)
    
    html = f"<div style='background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);'>"
    html += "<div style='color: var(--muted); font-size: 11px; margin-bottom: 10px;'>🔥 TOP 3 TRENDING ITEM (30 HARI TERAKHIR)</div>"
    
    for item, qty in top_items.items():
        html += f"<div style='font-size: 12px; margin-bottom: 8px; border-bottom: 1px solid var(--border); padding-bottom: 4px;'>"
        html += f"<b>{item}</b><br><span style='color: var(--green);'>Terjual: {qty:,.0f} Pcs</span></div>"
    
    html += "</div>"
    return {"type": "html", "response": html}

def calculate_math(expression):
    try:
        # Bersihkan kalimat, ambil hanya angka dan operator matematika dasar
        clean_expr = re.sub(r'[^\d\+\-\*\/\(\)\.]', '', expression)
        if not clean_expr: return None
            
        result = eval(clean_expr, {"__builtins__": None}, {})
        formatted_result = f"{float(result):,.2f}".rstrip('0').rstrip('.')
        if formatted_result.endswith(','): formatted_result = formatted_result[:-1]
        
        html = f"""
        <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
            <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px;">🧮 HASIL KALKULATOR</div>
            <div style="font-size: 13px; color: var(--text); margin-bottom: 5px;">{clean_expr} =</div>
            <div style="font-weight: bold; color: var(--accent); font-size: 18px;">{formatted_result}</div>
        </div>
        """
        return {"type": "html", "response": html}
    except Exception:
        return None

# ==========================================
# 0B. UTILITY: PENGHITUNG HARI (SELISIH TANGGAL)
# ==========================================
def calculate_days_diff(date1_str, date2_str):
    def parse_indo_date(ds):
        ds = str(ds).lower().strip()
        if ds in ['hari ini', 'sekarang']: return datetime.now()
        if ds in ['besok']: return datetime.now() + pd.Timedelta(days=1)
        if ds in ['kemarin']: return datetime.now() - pd.Timedelta(days=1)
        
        for m_txt, m_num in MONTHS_ID.items():
            ds = re.sub(rf'\b{m_txt}\b', f'-{m_num}-', ds)
            
        try:
            return pd.to_datetime(ds, dayfirst=True)
        except:
            return None

    d1 = parse_indo_date(date1_str)
    d2 = parse_indo_date(date2_str)
    
    if d1 and d2:
        diff = abs((d2 - d1).days)
        html = f"""
        <div style="background: var(--bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
            <div style="color: var(--muted); font-size: 11px; margin-bottom: 5px;">📅 SELISIH HARI</div>
            <div style="font-size: 12px; color: var(--text); margin-bottom: 5px;">Jarak antara <b>{d1.strftime('%d %b %Y')}</b> dan <b>{d2.strftime('%d %b %Y')}</b> adalah:</div>
            <div style="font-weight: bold; color: var(--accent); font-size: 18px;">{diff} Hari</div>
        </div>
        """
        return {"type": "html", "response": html}
    return None
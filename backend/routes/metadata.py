from flask import Blueprint, current_app, jsonify

metadata_bp = Blueprint("metadata", __name__)


@metadata_bp.route("/api/metadata")
def get_metadata():
    df = current_app.config.get("DF_KSU")
    if df is not None and not df.empty:
        min_date = df["tglnominatif"].min()
        max_date = df["tglnominatif"].max()

        bulan_indo = [
            "",
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember",
        ]

        tgl_terakhir = f"{max_date.day} {bulan_indo[max_date.month]} {max_date.year}"

        return jsonify(
            {
                "start_year": int(min_date.year),
                "end_year": int(max_date.year),
                "last_import": tgl_terakhir,
            }
        )

    return jsonify({"start_year": 2021, "end_year": 2026, "last_import": "Belum ada data"})
#!/bin/sh
# Kunlik zaxira nusxa (CONTRACT.md §18.3): Postgres (pg_dump -Fc) + uploads volume.
#
#   backup.sh        — har kuni BACKUP_HOUR da (Toshkent vaqti), to'xtovsiz
#   backup.sh now    — bir marta, hozir
#
# Fayllar /backups ga (compose'da deploy/backups/), avval .partial bo'lib
# yoziladi — yarim qolgan nusxa hech qachon tayyordek ko'rinmaydi.
set -eu

: "${POSTGRES_USER:?}" "${POSTGRES_PASSWORD:?}" "${POSTGRES_DB:?}"
BACKUP_HOUR="${BACKUP_HOUR:-3}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
DIR=/backups
export PGPASSWORD="$POSTGRES_PASSWORD"

backup() {
    stamp=$(date +%Y-%m-%d_%H%M)
    db="$DIR/tryjob_$stamp.dump"
    files="$DIR/uploads_$stamp.tar.gz"
    # `backup || …` ichida `set -e` ishlamaydi — har qadam o'zi tekshiriladi,
    # aks holda yarim dump ham to'liq nomga ko'chib ketardi
    pg_dump -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$db.partial" || return 1
    mv "$db.partial" "$db" || return 1
    tar -czf "$files.partial" -C /data uploads || return 1
    mv "$files.partial" "$files" || return 1
    # eskilari va avvalgi muvaffaqiyatsiz urinish qoldiqlari
    find "$DIR" -maxdepth 1 \( -name 'tryjob_*.dump' -o -name 'uploads_*.tar.gz' \) -mtime +"$BACKUP_KEEP_DAYS" -delete
    find "$DIR" -maxdepth 1 -name '*.partial' -mmin +60 -delete
    echo "$(date '+%F %T') zaxira tayyor: $(basename "$db") ($(du -h "$db" | cut -f1)), $(basename "$files")"
}

if [ "${1:-}" = "now" ]; then
    backup
    exit 0
fi

while true; do
    now=$(date +%s)
    next=$(date -d "today $BACKUP_HOUR:00" +%s)
    [ "$next" -le "$now" ] && next=$(date -d "tomorrow $BACKUP_HOUR:00" +%s)
    sleep $((next - now))
    # bitta muvaffaqiyatsiz kun servisni to'xtatmasin — log'da ko'rinadi, ertaga yana urinadi
    backup || echo "$(date '+%F %T') ZAXIRA XATO" >&2
done

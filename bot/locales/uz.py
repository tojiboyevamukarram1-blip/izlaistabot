"""O'zbek tili (Lotin alifbosi) matnlari va xabarlar to'plami."""

START_MESSAGE = (
    "👋 <b>Assalomu alaykum!</b>\n\n"
    "Men <b>Instagram</b>, <b>YouTube</b> va <b>Pinterest</b> platformalaridan "
    "media (video, musiqa, rasm) yuklab beruvchi tezkor botman.\n\n"
    "📌 <b>Qo'llab-quvvatlanadigan havolalar:</b>\n"
    "• <b>Instagram:</b> Reels, post videolari, karusel rasmlar\n"
    "• <b>YouTube:</b> Shorts, oddiy videolar, MP3 audio\n"
    "• <b>Pinterest:</b> Rasmlar (asl sifatda), videolar\n\n"
    "🚀 <i>Foydalanish uchun menga yuqoridagi platformalardan birining havolasini yuboring!</i>"
)

HELP_MESSAGE = (
    "📖 <b>Qo'llanma va yordam</b>\n\n"
    "1️⃣ Instagram, YouTube yoki Pinterest'dan xohlagan videongiz yoki rasmingiz havolasini (linkini) nusxalang.\n"
    "2️⃣ Havolani ushbu botga xabar sifatida yuboring.\n"
    "3️⃣ YouTube uchun kerakli sifat (1080p, 720p, MP3 va h.k.) tugmasini bosing.\n"
    "4️⃣ Bot faylni yuklab, sizga Telegram orqali yuboradi.\n\n"
    "⚡ <b>Buyruqlar:</b>\n"
    "/start — Botni ishga tushirish\n"
    "/help — Qo'llanma\n"
    "/status — Bot holati va statistika\n"
    "/cancel — Joriy amalni bekor qilish\n\n"
    "⚠️ <i>Eslatma: Faqat ochiq (public) postlar yuklanadi. Yopiq profillar va DRM himoyalangan kontent yuklanmaydi.</i>"
)

STATUS_MESSAGE = (
    "📊 <b>Bot holati:</b>\n\n"
    "🟢 <b>Tizim:</b> Faol va barqaror\n"
    "⚡ <b>Faol yuklashlar:</b> {active_downloads} / {max_downloads}\n"
    "💾 <b>Kesh xizmati:</b> {cache_status}\n"
    "📦 <b>Telegram yuklash chegarasi:</b> {max_size_mb} MB gacha\n"
    "⏱ <b>Maksimal davomiylik:</b> {max_duration_min} daqiqa"
)

CANCEL_SUCCESS = "🛑 Joriy amal bekor qilindi."
NOTHING_TO_CANCEL = "Hozirda bekor qilinadigan faol yuklash jarayoni yo'q."
ACCESS_DENIED = "⛔ Kechirasiz, ushbu bot shaxsiy foydalanish uchun sozlangan va faqat bot egasi uchun xizmat ko'rsatadi."
RETRYING_DOWNLOAD = "🔄 Tarmoq uzilishi kuzatildi, qayta urinilmoqda ({attempt}/{max_attempts})..."

# Validation & Detection
CHECKING_URL = "🔍 Havola tekshirilmoqda va ma'lumot olinmoqda..."
INVALID_URL = "❌ Noto'g'ri havola formati. Iltimos, haqiqiy URL manzil yuboring."
SSRF_BLOCKED = "⛔ Xavfsizlik tufayli ushbu manzilga kirish taqiqlangan (ichki tarmoq manzillari bloklangan)."
UNSUPPORTED_PLATFORM = (
    "⚠️ Faqat <b>Instagram</b>, <b>YouTube</b> va <b>Pinterest</b> havolalari qo'llab-quvvatlanadi.\n\n"
    "Iltimos, ushbu platformalarga tegishli havola yuboring."
)

FETCHING_METADATA_ERROR = (
    "❌ Havola bo'yicha ma'lumotni olib bo'lmadi.\n"
    "Ehtimol, havola noto'g'ri, video o'chirilgan yoki profil yopiq (shaxsiy)."
)

MEDIA_RESTRICTED = (
    "⚠️ <b>Kontent cheklangan!</b>\n\n"
    "Ushbu video muallif tomonidan auditoriya yoki yosh bo'yicha cheklangan "
    "(faqat Instagram hisobiga kirgan foydalanuvchilar ko'ra oladi). "
    "Ochiq holda yuklab bo'lmaydi."
)

MEDIA_PRIVATE = (
    "🔒 <b>Yopiq profil!</b>\n\n"
    "Ushbu post yopiq (shaxsiy) profilga tegishli bo'lgani sababli yuklab bo'lmaydi."
)

MEDIA_NOT_FOUND = (
    "❌ <b>Mavjud emas!</b>\n\n"
    "Ushbu video o'chirilgan yoki havola noto'g'ri."
)

# Media info and selections
YOUTUBE_CHOOSE_QUALITY = (
    "🎬 <b>YouTube:</b> {title}\n"
    "⏱ <b>Davomiyligi:</b> {duration}\n"
    "👤 <b>Kanal:</b> {author}\n\n"
    "⬇️ <i>Kerakli video sifati yoki audioni tanlang:</i>"
)

PINTEREST_CHOOSE_FORMAT = (
    "📌 <b>Pinterest:</b> {title}\n\n"
    "⬇️ <i>Faylni qanday yuklab olishni xohlaysiz?</i>"
)

INSTAGRAM_POST_INFO = (
    "📸 <b>Instagram:</b> {title}\n"
    "👤 <b>Muallif:</b> {author}\n\n"
    "⬇️ <i>Yuklab olish formatini tanlang:</i>"
)

INSTAGRAM_CAROUSEL_DOWNLOAD = "📥 Karuseldagi barcha media fayllar ({count} ta) yuklanmoqda..."

# Progress & Download
DOWNLOADING_MEDIA = "⏳ Fayl serverga yuklab olinmoqda: <b>{percent}%</b>\nTezlik: {speed} | Qolgan vaqt: {eta}"
DOWNLOADING_NO_PERCENT = "⏳ Fayl serverga yuklab olinmoqda..."
PROCESSING_FFMPEG = "⚙️ Media qayta ishlanmoqda (FFmpeg)..."
UPLOADING_TELEGRAM = "📤 Telegram tarmog'iga yuborilmoqda..."
DELIVERY_COMPLETE = "✅ <b>Tayyor!</b> Marhamat, faylingiz:"

# Errors & Limits
FILE_TOO_LARGE = (
    "⚠️ <b>Fayl hajmi juda katta!</b>\n\n"
    "Fayl hajmi: ~<b>{size_mb:.1f} MB</b>\n"
    "Telegram Bot API limiti: <b>{limit_mb} MB</b>\n\n"
    "Iltimos, pastroq sifatni tanlang (masalan, 720p yoki 480p)."
)

DURATION_TOO_LONG = (
    "⚠️ <b>Video davomiyligi juda uzun!</b>\n\n"
    "Video davomiyligi: <b>{duration_min} daqiqa</b>\n"
    "Maksimal ruxsat etilgan davomiylik: <b>{limit_min} daqiqa</b>."
)

FORMAT_UNAVAILABLE = (
    "⚠️ Tanlangan format mavjud emas yoki platforma tomonidan cheklangan.\n"
    "Iltimos, boshqa sifatni tanlang."
)

RATE_LIMIT_HIT = (
    "⏳ <b>Iltimos, biroz kuting!</b>\n\n"
    "Siz qisqa vaqt ichida juda ko'p so'rov yubordingiz. "
    "Iltimos, {seconds} soniyadan so'ng qayta urinib ko'ring."
)

CONCURRENCY_LIMIT_HIT = (
    "⏳ Hozirda serverda yuklash navbati to'lgan.\n"
    "Sizning so'rovingiz navbatga qo'yildi, biroz kuting..."
)

GENERIC_ERROR = "❌ Xatolik yuz berdi: {error}\nIltimos, keyinroq qayta urinib ko'ring."

# Buttons
BTN_VIDEO_FORMAT = "🎬 {resolution} {size_label}"
BTN_AUDIO_MP3 = "🎵 MP3 Audio {size_label}"
BTN_AUDIO_ORIGINAL = "🎶 Asl audio {size_label}"
BTN_PINTEREST_PHOTO = "🖼 Rasm sifatida"
BTN_PINTEREST_DOC = "📁 Hujjat sifatida (asl sifat)"
BTN_PINTEREST_VIDEO = "🎬 Video sifatida"
BTN_INSTAGRAM_VIDEO = "🎬 Videoni yuklash"
BTN_INSTAGRAM_CAROUSEL = "📚 Barcha mediayni yuklash ({count} ta)"
BTN_CANCEL = "❌ Bekor qilish"

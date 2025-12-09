import os
import re

# مسیر فایل ترجمه
PO_FILE_PATH = os.path.join('translations', 'tr', 'LC_MESSAGES', 'messages.po')

# دیکشنری جامع ترجمه‌ها
TRANSLATIONS = {
    # --- General / Navbar / Footer ---
    "VestHub - Intelligent Trading. Automated.": "VestHub - Akıllı Ticaret. Otomatikleştirilmiş.",
    "Home": "Ana Sayfa",
    "Marketplace": "Pazar Yeri",
    "Invest": "Yatırım",
    "Plans": "Planlar",
    "About Us": "Hakkımızda",
    "Select Language": "Dil Seçin",
    "Toggle theme": "Temayı Değiştir",
    "Dashboard": "Panel",
    "Logout": "Çıkış Yap",
    "Log In": "Giriş Yap",
    "Sign Up Free": "Ücretsiz Kayıt Ol",
    "All rights reserved.": "Tüm hakları saklıdır.",
    "Contact Us": "İletişim",
    "Terms & Conditions": "Şartlar ve Koşullar",
    "Privacy Policy": "Gizlilik Politikası",
    "Risk Disclosure": "Risk Bildirimi",

    # --- About Page ---
    "Where Deep Market Experience Meets Future Technology. We are a collective of veteran traders and engineers building the tools real traders need.": 
        "Derin Piyasa Deneyiminin Geleceğin Teknolojisiyle Buluştuğu Yer. Gerçek yatırımcıların ihtiyaç duyduğu araçları inşa eden kıdemli yatırımcılar ve mühendislerden oluşan bir kolektifiz.",
    
    "Our Unique Advantage": "Benzersiz Avantajımız",
    "A Team Forged by Experience": "Deneyimle Yoğrulmuş Bir Ekip",
    "Market Experts": "Piyasa Uzmanları",
    "The Market Experts (20+ Years)": "Piyasa Uzmanları (20+ Yıl)",
    
    "Our core strategy is driven by senior analysts and quantitative traders with over two decades of active, in-the-trenches market experience. They are the architects of the trading algorithms (bots) tested and proven profitable in diverse market conditions. They don't just follow trends; they anticipate them.": 
        "Temel stratejimiz, yirmi yılı aşkın aktif piyasa deneyimine sahip kıdemli analistler ve kantitatif yatırımcılar tarafından yönlendirilmektedir. Onlar, çeşitli piyasa koşullarında test edilmiş ve kârlılığı kanıtlanmış ticaret algoritmalarının (botların) mimarlarıdır. Sadece trendleri takip etmezler; onları öngörürler.",
    
    "Innovative Engineers": "Yenilikçi Mühendisler",
    "The Innovative Engineers (AI Prowess)": "Yenilikçi Mühendisler (Yapay Zeka Yetkinliği)",
    
    "Complementing this experience is our senior development team, fluent in the latest software methodologies and AI. This team translates the complex strategies of our analysts into fast, secure, and intelligent tools. We build the tools that we ourselves use every single day.": 
        "Bu deneyimi tamamlayan, en son yazılım metodolojileri ve yapay zeka konusunda uzmanlaşmış kıdemli geliştirme ekibimizdir. Bu ekip, analistlerimizin karmaşık stratejilerini hızlı, güvenli ve akıllı araçlara dönüştürür. Her gün bizzat kullandığımız araçları inşa ediyoruz.",
    
    "Beyond Theory: A Proven Track Record": "Teorinin Ötesinde: Kanıtlanmış Bir Geçmiş",
    "We don't just talk about technology; we have implemented it at the highest levels.": "Sadece teknolojiden bahsetmiyoruz; onu en üst düzeylerde uyguladık.",
    "ERP System": "ERP Sistemi",
    "Complete Brokerage ERP": "Tam Aracı Kurum ERP",
    "Successfully built and deployed a complete ERP system for a licensed brokerage.": "Lisanslı bir aracı kurum için eksiksiz bir ERP sistemi başarıyla oluşturuldu ve dağıtıldı.",
    "CFD Platform": "CFD Platformu",
    "Ground-Up CFD Platform": "Sıfırdan CFD Platformu",
    "Designed and developed an entire CFD Brokerage platform infrastructure.": "Tüm CFD Aracı Kurum platform altyapısı tasarlandı ve geliştirildi.",
    "Integration": "Entegrasyon",
    "Enterprise Integration": "Kurumsal Entegrasyon",
    "Executed enterprise-level integration systems for high-availability processes.": "Yüksek kullanılabilirlik süreçleri için kurumsal düzeyde entegrasyon sistemleri yürütüldü.",
    "A 360-Degree Market Perspective": "360 Derece Piyasa Perspektifi",
    "At VestHub, nothing is left to chance. Our team structure covers every angle.": "VestHub'da hiçbir şey şansa bırakılmaz. Ekip yapımız her açıyı kapsar.",
    "Fundamental Analysis": "Temel Analiz",
    "Monitoring real-time economic news, data releases, and geopolitical events.": "Gerçek zamanlı ekonomik haberleri, veri bültenlerini ve jeopolitik olayları izleme.",
    "Technical Analysis": "Teknik Analiz",
    "Identifying market patterns, trends, support, and resistance levels.": "Piyasa modellerini, trendleri, destek ve direnç seviyelerini belirleme.",
    "AI & Algorithmic": "Yapay Zeka & Algoritmik",
    "Developing the next generation of advanced bots and analytical tools.": "Yeni nesil gelişmiş botlar ve analitik araçlar geliştirme.",
    "Ready to Join the Platform?": "Platforma Katılmaya Hazır Mısınız?",
    "Our tools are the product of thousands of hours of experience.": "Araçlarımız binlerce saatlik deneyimin ürünüdür.",
    "Get Started Now": "Şimdi Başlayın",

    # --- Learn Page ---
    "Investing: The Ultimate Insurance for Your Financial Future": "Yatırım: Finansal Geleceğiniz İçin Nihai Sigorta",
    "In a world of economic uncertainty, holding cash in a bank account means your purchasing power is quietly eroding. Saving is an excellent first step, but it isn't enough.": "Ekonomik belirsizlik dünyasında, banka hesabında nakit tutmak, satın alma gücünüzün sessizce eridiği anlamına gelir. Tasarruf etmek harika bir ilk adımdır, ancak yeterli değildir.",
    "Inflation is the silent, consistent force that diminishes the value of your hard-earned money. Investing is the critical bridge between \"saving\" and \"building wealth.\"": "Enflasyon, zor kazandığınız paranızın değerini azaltan sessiz ve tutarlı bir güçtür. Yatırım, \"tasarruf\" ile \"servet inşa etme\" arasındaki kritik köprüdür.",
    "Why Investing Is No Longer a Choice, But a Necessity": "Yatırım Neden Artık Bir Seçenek Değil, Bir Zorunluluktur",
    "We believe that smart investing is the cornerstone of future financial independence. Here’s why it is essential:": "Akıllı yatırımın gelecekteki finansal bağımsızlığın temel taşı olduğuna inanıyoruz. İşte neden gerekli olduğu:",
    "Your Shield Against Inflation": "Enflasyona Karşı Kalkanınız",
    "This is the most straightforward reason. If your money isn't growing, it's losing. The primary goal of investing is to outpace inflation, ensuring that 10, 20, or 30 years from now, your money has the same—or more—buying power than it does today.": "Bu en basit nedendir. Paranız büyümüyorsa, kaybediyordur. Yatırımın birincil amacı enflasyonu geçmek, 10, 20 veya 30 yıl sonra paranızın bugünkünden aynı -veya daha fazla- alım gücüne sahip olmasını sağlamaktır.",
    "Your \"Insurance\" for the Unexpected": "Beklenmedik Durumlar İçin \"Sigortanız\"",
    "A strong investment portfolio acts as your financial \"insurance policy.\" It is a far more effective and robust emergency fund that gives you the flexibility to navigate financial challenges without extreme stress or being forced into hasty, poor decisions.": "Güçlü bir yatırım portföyü, finansal \"sigorta poliçeniz\" gibi hareket eder. Aşırı stres yaşamadan veya aceleci, kötü kararlar almaya zorlanmadan finansal zorlukların üstesinden gelme esnekliği sağlayan çok daha etkili ve sağlam bir acil durum fonudur.",
    "The Engine for Your Major Goals": "Büyük Hedefleriniz İçin Motor",
    "We all have dreams: buying a home, funding a child's education, or enjoying a comfortable retirement. Investing is the engine that puts a realistic timeline on those dreams and transforms \"saving\" from a passive habit into an active strategy.": "Hepimizin hayalleri vardır: ev almak, bir çocuğun eğitimini finanse etmek veya rahat bir emekliliğin tadını çıkarmak. Yatırım, bu hayallere gerçekçi bir zaman çizelgesi koyan ve \"tasarrufu\" pasif bir alışkanlıktan aktif bir stratejiye dönüştüren motordur.",
    "The Power of Compound Interest": "Bileşik Faizin Gücü",
    "Albert Einstein called it the \"eighth wonder of the world.\" You don’t just earn returns on your original money; you earn returns": "Albert Einstein buna \"dünyanın sekizinci harikası\" demiştir. Sadece orijinal paranızdan getiri elde etmezsiniz; şu getirileri de elde edersiniz:",
    "on your returns": "kendi getirileriniz üzerinden",
    ". This \"snowball\" effect is the difference between a small savings pot and significant wealth.": ". Bu \"kartopu\" etkisi, küçük bir tasarruf potası ile önemli bir servet arasındaki farktır.",
    "\"But Isn't Investing Complicated?\"": "\"Ama Yatırım Karmaşık Değil mi?\"",
    "This is where VestHub comes in. We understand not everyone has the time or desire to become a pro trader. That is precisely why we created our Managed Investment Service.": "İşte VestHub burada devreye giriyor. Herkesin profesyonel bir yatırımcı olmak için zamanı veya isteği olmadığını anlıyoruz. Tam da bu yüzden Yönetilen Yatırım Hizmetimizi oluşturduk.",
    "We take the complexity out of the equation. Our expert team and AI algorithms do the heavy lifting.": "Denklemin karmaşıklığını ortadan kaldırıyoruz. Uzman ekibimiz ve yapay zeka algoritmalarımız ağır yükü sizin için kaldırıyor.",
    "How it Works: Simple & Secure": "Nasıl Çalışır: Basit & Güvenli",
    "Simple, Stress-Free Investing.": "Basit, Stressiz Yatırım.",
    "Gain all the benefits of investing without any of the stress.": "Yatırımın tüm faydalarını stressiz bir şekilde elde edin.",
    "View Investment Plans": "Yatırım Planlarını Gör",

    # --- Contact Page ---
    "Get in Touch": "İletişime Geçin",
    "Have questions about our investment plans or trading tools? We're here to help.": "Yatırım planlarımız veya ticaret araçlarımız hakkında sorularınız mı var? Yardımcı olmak için buradayız.",
    "Send us a message": "Bize bir mesaj gönderin",
    "Full Name": "Ad Soyad",
    "Your Name": "Adınız",
    "Email Address": "E-posta Adresi",
    "Phone Number": "Telefon Numarası",
    "(Optional)": "(İsteğe Bağlı)",
    "Subject": "Konu",
    "General Inquiry": "Genel Soru",
    "Technical Support": "Teknik Destek",
    "Billing & Payments": "Faturalandırma & Ödemeler",
    "Partnership": "Ortaklık",
    "Message": "Mesaj",
    "How can we help you?": "Size nasıl yardımcı olabiliriz?",
    "Send Message": "Mesaj Gönder",
    "Our Office": "Ofisimiz",
    "Open in Google Maps": "Google Haritalar'da Aç",
    "View on Google Maps": "Haritada Göster",
    "WhatsApp Support": "WhatsApp Destek",
    "Chat Now": "Sohbet Et",
    "Email Us": "Bize E-posta Gönder",

    # --- Privacy Policy ---
    "1. Information We Collect": "1. Topladığımız Bilgiler",
    "We collect information you provide directly to us, such as when you create an account, complete KYC verification, make a deposit, or communicate with support. This may include:": "Bir hesap oluşturduğunuzda, KYC doğrulamasını tamamladığınızda, para yatırdığınızda veya destekle iletişim kurduğunuzda bize doğrudan sağladığınız bilgileri topluyoruz. Bunlar şunları içerebilir:",
    "Personal identification information (Name, email address, phone number).": "Kişisel kimlik bilgileri (Ad, e-posta adresi, telefon numarası).",
    "Identity verification documents (Passport, ID card, utility bills).": "Kimlik doğrulama belgeleri (Pasaport, kimlik kartı, faturalar).",
    "Financial information (Wallet addresses, transaction history).": "Finansal bilgiler (Cüzdan adresleri, işlem geçmişi).",
    "2. How We Use Your Information": "2. Bilgilerinizi Nasıl Kullanıyoruz",
    "We use the collected information to:": "Toplanan bilgileri şu amaçlarla kullanıyoruz:",
    "Provide, maintain, and improve our services.": "Hizmetlerimizi sağlamak, sürdürmek ve geliştirmek.",
    "Process transactions and send related notifications.": "İşlemleri gerçekleştirmek ve ilgili bildirimleri göndermek.",
    "Verify your identity and prevent fraud.": "Kimliğinizi doğrulamak ve dolandırıcılığı önlemek.",
    "Comply with legal obligations.": "Yasal yükümlülüklere uymak.",
    "3. Data Security": "3. Veri Güvenliği",
    "We implement appropriate technical and organizational measures to protect your personal data against unauthorized access, alteration, disclosure, or destruction. This includes encryption, two-factor authentication (2FA) support, and secure server infrastructure.": "Kişisel verilerinizi yetkisiz erişime, değişikliğe, ifşaya veya imhaya karşı korumak için uygun teknik ve organizasyonel önlemleri uyguluyoruz. Buna şifreleme, iki faktörlü kimlik doğrulama (2FA) desteği ve güvenli sunucu altyapısı dahildir.",
    "4. Sharing of Information": "4. Bilgilerin Paylaşımı",
    "We do not sell your personal data. We may share your information with third-party service providers (e.g., email delivery services) only to the extent necessary to provide our services, or when required by law.": "Kişisel verilerinizi satmıyoruz. Bilgilerinizi üçüncü taraf hizmet sağlayıcılarla (örneğin, e-posta teslim hizmetleri) yalnızca hizmetlerimizi sağlamak için gerekli olduğu ölçüde veya yasalar gerektirdiğinde paylaşabiliriz.",
    "5. Cookies": "5. Çerezler",
    "We use cookies to improve your experience on our site. You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent.": "Sitemizdeki deneyiminizi geliştirmek için çerezler kullanıyoruz. Tarayıcınıza tüm çerezleri reddetmesi veya bir çerez gönderildiğinde bunu belirtmesi talimatını verebilirsiniz.",
    "6. Contact Us": "6. Bize Ulaşın",
    "If you have any questions about this Privacy Policy, please contact us at support@vesthub.org.": "Bu Gizlilik Politikası hakkında herhangi bir sorunuz varsa, lütfen support@vesthub.org adresinden bizimle iletişime geçin.",
    "&larr; Back to Home": "&larr; Ana Sayfaya Dön",

    # --- Risk Disclosure ---
    "Risk Disclosure Statement": "Risk Bildirimi Beyanı",
    "Important Notice:": "Önemli Uyarı:",
    "Trading and investing in financial markets involve a significant level of risk and may not be suitable for all investors. You should carefully consider your investment objectives, level of experience, and risk appetite before deciding to invest.": "Finansal piyasalarda ticaret ve yatırım yapmak önemli düzeyde risk içerir ve tüm yatırımcılar için uygun olmayabilir. Yatırım yapmaya karar vermeden önce yatırım hedeflerinizi, deneyim seviyenizi ve risk iştahınızı dikkatlice değerlendirmelisiniz.",
    "1. General Risk Warning": "1. Genel Risk Uyarısı",
    "There is a possibility that you may sustain a loss of some or all of your initial investment and therefore you should not invest money that you cannot afford to lose. You should be aware of all the risks associated with trading and seek advice from an independent financial advisor if you have any doubts.": "Başlangıç yatırımınızın bir kısmını veya tamamını kaybetme ihtimaliniz vardır ve bu nedenle kaybetmeyi göze alamayacağınız parayla yatırım yapmamalısınız. Ticaretle ilgili tüm risklerin farkında olmalı ve herhangi bir şüpheniz varsa bağımsız bir finansal danışmandan tavsiye almalısınız.",
    "2. Market Volatility": "2. Piyasa Oynaklığı",
    "Cryptocurrency and financial markets are highly volatile. Prices can fluctuate significantly in a short period due to various factors including regulatory changes, market sentiment, and technical issues. VestHub cannot guarantee profits or freedom from loss.": "Kripto para ve finansal piyasalar oldukça değişkendir. Fiyatlar, düzenleyici değişiklikler, piyasa duyarlılığı ve teknik sorunlar dahil olmak üzere çeşitli faktörler nedeniyle kısa sürede önemli ölçüde dalgalanabilir. VestHub kar veya kayıptan muafiyet garanti edemez.",
    "3. Technology Risk": "3. Teknoloji Riski",
    "While VestHub employs advanced security measures, there are inherent risks associated with using internet-based trading systems, including, but not limited to, the failure of hardware, software, and internet connections.": "VestHub gelişmiş güvenlik önlemleri kullanmasına rağmen, donanım, yazılım ve internet bağlantılarının arızalanması dahil ancak bunlarla sınırlı olmamak üzere internet tabanlı ticaret sistemlerinin kullanılmasıyla ilişkili doğal riskler vardır.",
    "4. No Financial Advice": "4. Finansal Tavsiye Değildir",
    "The content provided on the VestHub website, including investment plans and market data, is for informational purposes only and does not constitute financial advice. All investment decisions are made at your own risk.": "Yatırım planları ve piyasa verileri dahil olmak üzere VestHub web sitesinde sağlanan içerik yalnızca bilgilendirme amaçlıdır ve finansal tavsiye niteliği taşımaz. Tüm yatırım kararları kendi riskiniz altındadır.",

    # --- Terms & Conditions ---
    "1. Introduction": "1. Giriş",
    "Welcome to VestHub. By accessing our website and using our services, you agree to be bound by these Terms and Conditions. Please read them carefully.": "VestHub'a hoş geldiniz. Web sitemize erişerek ve hizmetlerimizi kullanarak, bu Şartlar ve Koşullara bağlı kalmayı kabul edersiniz. Lütfen bunları dikkatlice okuyun.",
    "2. Eligibility": "2. Uygunluk",
    "To use our services, you must be at least 18 years old and capable of forming a binding contract. You must not be a resident of any jurisdiction where accessing or using our services is prohibited.": "Hizmetlerimizi kullanmak için en az 18 yaşında olmanız ve bağlayıcı bir sözleşme yapabilmeniz gerekir. Hizmetlerimize erişmenin veya kullanmanın yasak olduğu herhangi bir yargı bölgesinde ikamet etmemelisiniz.",
    "3. Account Registration and Security": "3. Hesap Kaydı ve Güvenlik",
    "You agree to provide accurate and complete information during the registration process. You are responsible for maintaining the confidentiality of your account credentials, including your password and 2FA codes. VestHub is not liable for any loss or damage arising from your failure to protect your account information.": "Kayıt işlemi sırasında doğru ve eksiksiz bilgi vermeyi kabul edersiniz. Şifreniz ve 2FA kodlarınız dahil olmak üzere hesap kimlik bilgilerinizin gizliliğini korumaktan siz sorumlusunuz. VestHub, hesap bilgilerinizi koruyamamanızdan kaynaklanan herhangi bir kayıp veya hasardan sorumlu değildir.",
    "4. Identity Verification (KYC)": "4. Kimlik Doğrulama (KYC)",
    "To comply with anti-money laundering (AML) regulations, VestHub requires all users to complete Identity Verification (KYC) before withdrawing funds. We reserve the right to request additional documents or suspend accounts that fail to provide satisfactory proof of identity.": "Kara para aklamayı önleme (AML) düzenlemelerine uymak için VestHub, tüm kullanıcıların para çekmeden önce Kimlik Doğrulamasını (KYC) tamamlamasını gerektirir. Ek belgeler talep etme veya tatmin edici kimlik kanıtı sunmayan hesapları askıya alma hakkımız saklıdır.",
    "5. Investment Services": "5. Yatırım Hizmetleri",
    "VestHub provides automated trading and investment plans. While we strive for accuracy, past performance is not indicative of future results. You acknowledge that all investments carry risk, and you are solely responsible for your investment decisions.": "VestHub otomatik ticaret ve yatırım planları sunar. Doğruluk için çabalasak da, geçmiş performans gelecekteki sonuçların göstergesi değildir. Tüm yatırımların risk taşıdığını ve yatırım kararlarınızdan yalnızca sizin sorumlu olduğunuzu kabul edersiniz.",
    "6. Deposits and Withdrawals": "6. Para Yatırma ve Çekme",
    "Deposits must be made using the supported payment methods. Withdrawals are processed according to our withdrawal policy and may be subject to security checks. You agree not to deposit funds originating from illegal activities.": "Para yatırma işlemleri desteklenen ödeme yöntemleri kullanılarak yapılmalıdır. Para çekme işlemleri para çekme politikamıza göre işlenir ve güvenlik kontrollerine tabi olabilir. Yasa dışı faaliyetlerden kaynaklanan fonları yatırmamayı kabul edersiniz.",
    "7. Limitation of Liability": "7. Sorumluluk Sınırlaması",
    "VestHub shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from your access to or use of or inability to access or use the services.": "VestHub, hizmetlere erişiminizden veya kullanımınızdan veya hizmetlere erişememenizden veya kullanamamanızdan kaynaklanan kar, veri, kullanım, şerefiye veya diğer maddi olmayan kayıplar dahil ancak bunlarla sınırlı olmamak üzere dolaylı, arızi, özel, sonuç olarak ortaya çıkan veya cezai zararlardan sorumlu olmayacaktır.",
    "8. Changes to Terms": "8. Şartlarda Değişiklikler",
    "We reserve the right to modify these terms at any time. We will notify users of any significant changes via email or a notice on our website.": "Bu şartları istediğimiz zaman değiştirme hakkımız saklıdır. Önemli değişiklikleri e-posta veya web sitemizdeki bir bildirim yoluyla kullanıcılara bildireceğiz.",

    # --- Marketplace ---
    "Meet Vetrix 1": "Vetrix 1 ile Tanışın",
    "The next generation of intelligent trading bots. Built by veteran traders with 12+ years of market experience, for professional traders and institutions.": "Akıllı ticaret botlarının yeni nesli. Profesyonel tüccarlar ve kurumlar için, 12 yılı aşkın piyasa deneyimine sahip usta tüccarlar tarafından tasarlandı.",
    "Stop using retail toys or overpaying for institutional platforms. Vetrix 1 bridges the gap.": "Perakende oyuncaklarını kullanmayı veya kurumsal platformlara fazla ödeme yapmayı bırakın. Vetrix 1 boşluğu dolduruyor.",
    "Start Trading Now": "Şimdi İşleme Başlayın",
    "For Institutions": "Kurumlar İçin",
    "The Vetrix 1 Advantage: Why We Are Different": "Vetrix 1 Avantajı: Neden Farklıyız",
    "Aligned Profit Model": "Hizalanmış Kar Modeli",
    # FIX: Double percent signs (%%) to escape formatting error
    "We win when you win. Unlike subscription-based bots that don't care if you profit, Vetrix operates on a **Profit-Sharing** model. Our incentives are 100%% aligned with your success.": "Siz kazandığınızda biz de kazanırız. Kâr edip etmediğinizi önemsemeyen abonelik tabanlı botların aksine, Vetrix bir **Kar Paylaşımı** modeliyle çalışır. Teşviklerimiz %%100 başarınızla uyumludur.",
    "Technical Superiority": "Teknik Üstünlük",
    "Built in C# for low-latency execution. We use **real Range Bar data** from futures markets, not unreliable CFD data. Our algorithm is volume-independent, making it universally adaptable.": "Düşük gecikmeli işlem için C# ile oluşturuldu. Güvenilmez CFD verileri yerine vadeli işlem piyasalarından **gerçek Aralık Çubuğu (Range Bar) verileri** kullanıyoruz. Algoritmamız hacimden bağımsızdır, bu da onu evrensel olarak uyarlanabilir kılar.",
    "Adaptive Risk Management": "Uyarlanabilir Risk Yönetimi",
    "Vetrix 1 features a multi-layered, adaptive money management system. It's designed to control daily drawdowns and manage risk intelligently, protecting your capital during volatile conditions.": "Vetrix 1, çok katmanlı, uyarlanabilir bir para yönetim sistemine sahiptir. Günlük düşüşleri kontrol etmek ve riski akıllıca yönetmek, dalgalı koşullarda sermayenizi korumak için tasarlanmıştır.",
    "How We Compare": "Nasıl Karşılaştırırız",
    "Retail Bot Marketplaces": "Perakende Bot Pazarları",
    "Retail Crypto Bots (e.g., 3Commas)": "Perakende Kripto Botları (örn. 3Commas)",
    "Target Audience": "Hedef Kitle",
    "Funds, Companies, Pro Traders": "Fonlar, Şirketler, Profesyonel Tüccarlar",
    "Retail Traders": "Perakende Tüccarlar",
    "Retail Crypto Users": "Perakende Kripto Kullanıcıları",
    "Revenue Model": "Gelir Modeli",
    "Profit-Sharing (Aligned)": "Kar Paylaşımı (Hizalanmış)",
    "Subscription / Direct Sale": "Abonelik / Doğrudan Satış",
    "Subscription": "Abonelik",
    "Core Technology": "Çekirdek Teknoloji",
    "C# (Low-Latency)": "C# (Düşük Gecikme)",
    "Varies (Often Python, JS)": "Değişken (Genellikle Python, JS)",
    "Varies": "Değişken",
    "Data Source": "Veri Kaynağı",
    "Real Futures Range Bars": "Gerçek Vadeli İşlem Aralık Çubukları",
    "Often unreliable CFD data": "Genellikle güvenilmez CFD verileri",
    "Exchange API": "Borsa API'si",
    "Risk Management": "Risk Yönetimi",
    "Adaptive, Multi-Level, DD Control": "Uyarlanabilir, Çok Seviyeli, DD Kontrolü",
    "Basic / None": "Temel / Yok",
    "User-dependent Stop-Loss": "Kullanıcıya bağlı Zarar Durdurma",
    "Transparency": "Şeffaflık",
    "Full (Real Statements)": "Tam (Gerçek Ekstreler)",
    "Low (Backtests only)": "Düşük (Sadece Geriye Dönük Testler)",
    "User-dependent": "Kullanıcıya bağlı",
    "Built for Professionals": "Profesyoneller İçin Tasarlandı",
    "For Individual Pro Traders": "Bireysel Profesyonel Tüccarlar İçin",
    "Run Vetrix 1 directly on your own trading account. You maintain full control over your funds. We provide the execution, risk management, and performance monitoring.": "Vetrix 1'i doğrudan kendi ticaret hesabınızda çalıştırın. Fonlarınız üzerinde tam kontrolü elinizde tutarsınız. Biz yürütme, risk yönetimi ve performans izleme sağlıyoruz.",
    "Min. Capital:": "Min. Sermaye:",
    "Model:": "Model:",
    # FIX: Double percent signs (%%)
    "Profit-Sharing (50/50 above 2%% threshold)": "Kar Paylaşımı (%%2 eşiğinin üzerinde 50/50)",
    "Connection:": "Bağlantı:",
    "Direct API (NinjaTrader, AMP, etc.)": "Doğrudan API (NinjaTrader, AMP, vb.)",
    "For Institutions & Funds (B2B)": "Kurumlar ve Fonlar İçin (B2B)",
    "Integrate Vetrix 1 into your fund's portfolio to diversify strategies and stabilize returns. Ideal for fixed-income funds, prop firms, and corporations with idle capital.": "Stratejileri çeşitlendirmek ve getirileri istikrara kavuşturmak için Vetrix 1'i fonunuzun portföyüne entegre edin. Sabit getirili fonlar, prop firmaları ve atıl sermayesi olan şirketler için idealdir.",
    "B2B Agreement (PoC required)": "B2B Anlaşması (PoC gereklidir)",
    "Features:": "Özellikler:",
    "SLA, Custom Risk Overlays, Managerial Reporting": "SLA, Özel Risk Katmanları, Yönetimsel Raporlama",
    "Request a B2B Demo": "B2B Demosu Talep Edin",
    "Key Features": "Temel Özellikler",
    "Multi-Platform Ready": "Çoklu Platforma Hazır",
    "Modular architecture designed for NinjaTrader, MetaTrader, Tradovate, and more.": "NinjaTrader, MetaTrader, Tradovate ve daha fazlası için tasarlanmış modüler mimari.",
    "Universal Market Adaptability": "Evrensel Piyasa Uyumluluğu",
    "Data-independence allows Vetrix to run seamlessly on Futures, Crypto Futures, Forex, and Commodities.": "Veri bağımsızlığı, Vetrix'in Vadeli İşlemler, Kripto Vadeli İşlemler, Forex ve Emtialar üzerinde sorunsuz çalışmasını sağlar.",
    "AI & Machine Learning Ready": "Yapay Zeka ve Makine Öğrenimine Hazır",
    "Built with a foundation for future AI-driven adaptive learning and self-optimization.": "Gelecekteki yapay zeka odaklı uyarlanabilir öğrenme ve kendi kendine optimizasyon için bir temelle oluşturulmuştur.",
    "Multi-Risk Coverage": "Çoklu Risk Kapsamı",
    "Tailored profit-to-risk optimization based on your selected risk profile.": "Seçtiğiniz risk profiline göre uyarlanmış kar-risk optimizasyonu.",
    "Multi-Strategy Management": "Çoklu Strateji Yönetimi",
    "Enables portfolio diversification and overall risk reduction by running multiple strategies.": "Birden fazla strateji çalıştırarak portföy çeşitlendirmesi ve genel risk azaltımı sağlar.",
    "API & Copy Trading": "API ve Kopya Ticareti",
    "Direct connectivity with global brokers (like AMP Broker) and exchanges (like Binance).": "Küresel brokerlar (AMP Broker gibi) ve borsalarla (Binance gibi) doğrudan bağlantı.",
    "Ready to Upgrade Your Trading?": "Ticaretinizi Yükseltmeye Hazır Mısınız?",
    "Join VestHub today and get access to Vetrix 1. Stop guessing, start performing.": "VestHub'a bugün katılın ve Vetrix 1'e erişin. Tahmin etmeyi bırakın, performans göstermeye başlayın.",
    
    # --- Missing Strings / Specific Fixes ---
    "Annual Return (%)": "Yıllık Getiri (%%)",
    "Annual Return": "Yıllık Getiri",
    "100% (up to 2%), then 50%": "%%100 (%%2'ye kadar), sonra %%50",
    "2%)": "%%2)",
    "Profit Threshold (2% = $1,200)": "Kar Eşiği (%%2 = $1,200)",
    "No Fee (Below 2%)": "Ücret Yok (%%2 Altında)",
    "Referral Bonus Percentage (%)": "Referans Bonusu Yüzdesi (%%)",
    "Low": "Düşük",
    "Medium": "Orta",
    "High": "Yüksek",
    "Less than 10%": "%%10'dan az",
    "10% - 25%": "%%10 - %%25",
    "25% - 50%": "%%25 - %%50",
    "More than 50%": "%%50'den fazla",
    "Guaranteed 3% return.": "Garantili %%3 getiri.",
    "50% chance of 10% return, 50% chance of 0%.": "%%50 ihtimalle %%10 getiri, %%50 ihtimalle %%0.",
    "50% chance of 50% return, 50% chance of -20% loss.": "%%50 ihtimalle %%50 getiri, %%50 ihtimalle -%%20 kayıp.",
    "0% - 10%": "%%0 - %%10",
    "10% - 30%": "%%10 - %%30",
    "30% - 60%": "%%30 - %%60",
    "More than 60%": "%%60'tan fazla"
}

def fix_percentages(text):
    """Replaces single % with %% unless it looks like a format specifier."""
    if not text: return text
    # اگر در متن "%%" وجود دارد، فرض می‌کنیم درست است.
    # اما اگر "% " (درصد و فاصله) یا "%1" (درصد و عدد) وجود دارد، باید "%%" شود.
    # ساده‌ترین راه: هر % که دوتایی نیست را دوتایی کنیم.
    
    # 1. Temporarily replace valid double percents
    text = text.replace('%%', '__DOUBLE_PERCENT__')
    
    # 2. Replace single percents with double
    text = text.replace('%', '%%')
    
    # 3. Restore double percents (which are now quadruple %%%% -> we want %%)
    # Wait, simple replace % -> %% works if we assume NO variables are used in these strings.
    # In this project, most strings are static text.
    # So converting ALL % to %% is safe for static text.
    
    text = text.replace('__DOUBLE_PERCENT__', '%%')
    return text

def main():
    if not os.path.exists(PO_FILE_PATH):
        print(f"❌ File not found: {PO_FILE_PATH}")
        return

    print("📖 Reading messages.po...")
    with open(PO_FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    # حذف خط fuzzy از هدر
    lines = [l for l in lines if not l.strip() == "#, fuzzy"]

    while i < len(lines):
        line = lines[i]
        
        if line.startswith('msgid "'):
            # استخراج msgid (شامل چند خطی)
            msgid = line.strip()[7:-1]
            j = 1
            while i + j < len(lines) and lines[i+j].strip().startswith('"'):
                msgid += lines[i+j].strip()[1:-1]
                j += 1
            
            # ذخیره خطوط msgid در بافر
            msgid_buffer = lines[i:i+j]
            i += j
            
            # حالا به دنبال msgstr می‌گردیم
            if i < len(lines) and lines[i].startswith('msgstr "'):
                # 1. آیا ترجمه آماده داریم؟
                translation = TRANSLATIONS.get(msgid)
                
                # 2. اگر ترجمه نداشتیم، ترجمه فعلی داخل فایل را برداریم و فیکس کنیم
                if not translation:
                    current_trans = lines[i].strip()[8:-1]
                    k = 1
                    while i + k < len(lines) and lines[i+k].strip().startswith('"'):
                        current_trans += lines[i+k].strip()[1:-1]
                        k += 1
                    if current_trans:
                        translation = fix_percentages(current_trans)
                    # اسکیپ کردن خطوط msgstr فعلی
                    i += k - 1 # (loop increments i later)
                else:
                    # اسکیپ کردن خطوط msgstr قدیمی
                    k = 1
                    while i + k < len(lines) and lines[i+k].strip().startswith('"'):
                        k += 1
                    i += k - 1

                # افزودن فلگ no-c-format اگر درصد دارد
                if translation and '%' in translation:
                    # چک کنیم قبلاً فلگ دارد یا نه
                    has_flag = False
                    if len(new_lines) > 0 and 'no-c-format' in new_lines[-1]: has_flag = True
                    if not has_flag and len(new_lines) > 1 and 'no-c-format' in new_lines[-2]: has_flag = True
                    
                    if not has_flag:
                        # پیدا کردن جای مناسب (قبل از msgid)
                        # msgid_buffer اولین خطش msgid است. قبل از آن کامنت‌ها هستند.
                        # ما اینجا قبل از msgid اضافه می‌کنیم.
                        new_lines.append("#, no-c-format, no-python-format\n")

                new_lines.extend(msgid_buffer)
                new_lines.append(f'msgstr "{translation or ""}"\n')
                i += 1
                continue
            else:
                # اگر msgstr پیدا نشد (نباید بشه)، بافر را می‌نویسیم
                new_lines.extend(msgid_buffer)
        else:
            new_lines.append(line)
            i += 1

    print("💾 Writing fixed messages.po...")
    with open(PO_FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print("🎉 Done! All issues fixed.")
    print("👉 Now run: pybabel compile -d translations")

if __name__ == "__main__":
    main()
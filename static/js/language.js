let currentLanguage =
    localStorage.getItem("language") || "en";


// ============================================
// TRANSLATIONS
// ============================================

const translations = {

    en: {

        company:
            "IOTrenetics Solutions",

        hero_title:
            "AI Denim Dye Consistency Inspection System",

        hero_description:
            "An AI-powered textile quality control platform developed for industrial denim inspection, LAB color analysis, Delta E comparison and intelligent dye recipe recommendation.",

        dashboard:
            "Dashboard",

        fabric:
            "Fabric Comparison",

        recipe:
            "Recipe Extraction",

        reports:
            "AI Reports",

        qc:
            "Quality Control",

        compare_btn:
            "Run Fabric Comparison",

        recipe_btn:
            "Generate AI Recipe",

        upload_reference:
            "Upload Reference Fabric",

        upload_test:
            "Upload Test Fabric",

        upload_sample:
            "Upload Denim Sample"

    },

    hi: {

        company:
            "आईओट्रेनेटिक्स सॉल्यूशंस",

        hero_title:
            "एआई डेनिम डाई कंसिस्टेंसी इंस्पेक्शन सिस्टम",

        hero_description:
            "यह एक एआई आधारित टेक्सटाइल क्वालिटी कंट्रोल प्लेटफॉर्म है जो डेनिम फैब्रिक की LAB कलर एनालिसिस, डेल्टा E तुलना और डाई रेसिपी रिकमेंडेशन के लिए बनाया गया है।",

        dashboard:
            "डैशबोर्ड",

        fabric:
            "कपड़ा तुलना",

        recipe:
            "रेसिपी एक्सट्रैक्शन",

        reports:
            "एआई रिपोर्ट्स",

        qc:
            "क्वालिटी कंट्रोल",

        compare_btn:
            "फैब्रिक तुलना शुरू करें",

        recipe_btn:
            "एआई रेसिपी बनाएं",

        upload_reference:
            "रेफरेंस फैब्रिक अपलोड करें",

        upload_test:
            "टेस्ट फैब्रिक अपलोड करें",

        upload_sample:
            "डेनिम सैंपल अपलोड करें"

    }
};


// ============================================
// APPLY LANGUAGE
// ============================================

function applyLanguage(){

    const t =
        translations[currentLanguage];

    // COMPANY

    setText(
        "company-text",
        t.company
    );

    // HERO

    setText(
        "hero-title",
        t.hero_title
    );

    setText(
        "hero-description",
        t.hero_description
    );

    // NAVIGATION

    setText(
        "dashboard-text",
        t.dashboard
    );

    setText(
        "fabric-text",
        t.fabric
    );

    setText(
        "recipe-text",
        t.recipe
    );

    setText(
        "reports-text",
        t.reports
    );

    setText(
        "qc-text",
        t.qc
    );

    // BUTTONS

    setText(
        "compare-btn",
        t.compare_btn
    );

    setText(
        "recipe-btn",
        t.recipe_btn
    );

    // LABELS

    setText(
        "upload-reference",
        t.upload_reference
    );

    setText(
        "upload-test",
        t.upload_test
    );

    setText(
        "upload-sample",
        t.upload_sample
    );

    // TOGGLE BUTTON

    const langBtn =
        document.getElementById("lang-btn");

    if(langBtn){

        langBtn.innerText =
            currentLanguage === "en"
            ? "हिन्दी"
            : "English";
    }
}


// ============================================
// HELPER
// ============================================

function setText(id, text){

    const el =
        document.getElementById(id);

    if(el){

        el.innerText = text;
    }
}


// ============================================
// TOGGLE LANGUAGE
// ============================================

function toggleLanguage(){

    currentLanguage =
        currentLanguage === "en"
        ? "hi"
        : "en";

    localStorage.setItem(
        "language",
        currentLanguage
    );

    applyLanguage();
}


// ============================================
// AUTO APPLY
// ============================================

window.addEventListener(
    "DOMContentLoaded",
    function(){

        applyLanguage();

    }
);
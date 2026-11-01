# בדיקת שוברים לחנות עם gift-card-shopping

"אני בחנות הזאת, איזה מהשוברים שלי מתאים?"

הסקיל מנחה את סוכן ה-AI לבדוק אילו שוברים או הטבות עשויים להתאים לחנות מסוימת. הבדיקה מפרידה בין מוצרי שובר שונים של אותו מנפיק, ובין קנייה בסניף, באתר או דרך מוכר בזירת מסחר. לצורך מחקר הסוכן בודק מקורות רשמיים ותנאי מימוש; כשאין ראיה מספקת, התשובה צריכה להישאר לא ודאית.

החבילה השיתופית כוללת הוראות מחקר ועזר מקומי לחיפוש בנתונים שסיפק המשתמש. ארנק השוברים הפרטי הוא קובץ נפרד עם השוברים וההטבות של המשתמש, ואינו חלק מהסקיל או מהריפו. ההתקנה לא יוצרת ארנק, לא מחברת חשבונות ולא טוענת נתונים אישיים. העזר המקומי קורא ארנק וקטלוג חיצוניים רק דרך קובץ הגדרות מפורש; הוא לא אוסף בעצמו רשימות חנויות.

הכלי לא קונה או מממש שוברים, לא מסנכרן יתרות ולא מבטיח שהקופה תכבד שובר. אין בחבילה קטלוג חנויות אמיתי. זהו מועמד בגרסה 0.1.0 עם [מגבלות ידועות](references/limits.md), ולא מוצר שנבדק במלואו. הבדיקות והדוגמאות משתמשות בנתונים סינתטיים בלבד ואינן הוכחה לשימוש בארנק אמיתי או לקבלת שובר בחנות.

## התקנה למשתמשים

אפשר להתקין באמצעות כלי [skills של Vercel Labs](https://github.com/vercel-labs/skills), בסוכן שנתמך על ידו, למשל Claude Code או Codex. לפי התיעוד הרשמי של המתקין נדרשת סביבת Node.js בגרסה 22.20 ומעלה. פקודת ההתקנה אינה משתמשת ב-Python:

```sh
npx skills add https://github.com/baruchiro/skills/tree/master/baruchiro/skills/gift-card-shopping
```

הריצו מתוך הפרויקט שבו תרצו להשתמש בסקיל, בחרו את הסוכן במסך ההתקנה ובדקו את היעד לפני האישור. ברירת המחדל היא התקנה לפרויקט הנוכחי; להתקנה לכל הפרויקטים אפשר להוסיף `-g`. התחביר לכתובת של תיקיית סקיל והאפשרויות מתועדים ב[מדריך הרשמי להתקנה](https://github.com/vercel-labs/skills/blob/main/docs/commands.md#skills-add). אל תתקינו במקביל את הטיוטה הישנה `merchant-voucher-lookup` לאותה מטרה.

לאחר ההתקנה אפשר לבקש מהסוכן: "בדוק אילו שוברים עשויים להתאים לחנות שבחרתי. שאל אותי על סוג השובר וערוץ הקנייה אם חסר מידע, ואל תפתח קבצים פרטיים בלי אישורי." למחקר במקורות ציבוריים הסוכן זקוק לכלי גישה לרשת. העזר המקומי האופציונלי דורש Python 3.10 ומעלה; התקנת הסקיל לא מתקינה את סביבת ההרצה ולא מכינה את הקבצים החיצוניים עבורכם.

## פרטיות והסכמה לפני שימוש

שמרו ארנק, הגדרות, קטלוג תפעולי ומטמון מחוץ לתיקיית הסקיל ולכל תיקיית Git. לפני קריאת ארנק אמיתי נדרשים אישור לקבצים המדויקים ובדיקה ידנית של התוכן. אל תמסרו קודים למימוש, PIN, ברקודים, מספרי כרטיס, פרטי התחברות או כתובות מימוש אישיות. יתרות מוסתרות כברירת מחדל ויש להציגן רק לפי בקשה מפורשת בשיחה.

גם שמות שוברים ופלט ללא סכומים הם מידע אישי שעשוי להגיע להיסטוריית השיחה ולספק המודל. הרצה מקומית אינה סביבת בידוד לפרטיות, והבדיקות הקיימות אינן מבטיחות דחייה של כל שדה רגיש או מניעת חשיפה בהודעות שגיאה. קראו את [כללי הפרטיות](references/privacy.md) ואת [המגבלות](references/limits.md) לפני מסירת נתונים אמיתיים. הרשאה למחקר ציבורי אינה הרשאה לקרוא, לשנות או לפרסם ארנק פרטי.

לפי נוהל הסקיל, לפני שימוש ראשון הסוכן צריך להסביר ולקבל הסכמה לכך שפערים ניתנים לשחזור יטופלו בתרומת תיקון לריפו. התקנה או קריאת התיעוד אינן הסכמה לפרסום: כל תרומה כפופה לאישורים הנדרשים, ללא מידע אישי. זהו נוהל עבודה מפורש, לא טלמטריה אוטומטית ולא תנאי נוסף ברישיון MIT. הפרטים ב[הוראות הסקיל](SKILL.md#required-improvement-contributions).

## מידע למתחזקים: מבנה, הדגמה ובדיקות

הסעיפים הבאים מתעדים את המועמד הקיים ואת בדיקות הפיתוח. פקודות Python כאן מיועדות להרצת העזר והבדיקות, ולא להתקנת הסקיל.

Migration and extension of the gift-card shopping procedure, with a local reverse-lookup helper previously drafted as `merchant-voucher-lookup`. One skill directory covers both research and lookup; no second live skill is installed.

## Layout

Like the adjacent `book-search` skill, the entry file is `SKILL.md` with YAML name/description/version/author/license/platform metadata. Executable helpers live in `scripts/`, guidance in `references/`, synthetic examples in `examples/`, checks in `tests/`. No `merchant_voucher_lookup` Python module is shipped.

## Requirements and demo

Python 3.10+, standard library only. Linux exercised; no network/account access. From this package directory, through `terminal`, copy the **synthetic** examples to a new private, non-Git directory:

```sh
mkdir -m 700 "$HOME/voucher-demo"
cp examples/*.json "$HOME/voucher-demo/"
python3 scripts/voucher_lookup.py validate --config "$HOME/voucher-demo/config.json"
python3 scripts/voucher_lookup.py lookup --config "$HOME/voucher-demo/config.json" --merchant Kravitz --channel physical --format text
```

Do not overwrite an existing private directory. These examples use brand labels for test readability but all eligibility, amounts, dates and source excerpts are invented. Reserved `example.invalid` URLs cannot prove acceptance. As examples age the lookup can change to conditional: freshness uses runtime time even with `--on`.

A missing/unreadable config is an error, not “no vouchers.” Real use requires separately approved and manually reviewed external inputs. See [data model](references/data-model.md), [privacy](references/privacy.md), [research rules](references/research-rules.md) and [limits](references/limits.md).

## Checks

Through `terminal`, from this directory:

```sh
python3 tests/smoke_cli.py
python3 tests/test_voucher_lookup.py
```

`smoke_cli.py` runs only validation and a synthetic lookup and checks that the documented entry point works, output is marked synthetic, amounts are hidden, and five distinct fixture holdings are returned. It also counts the existing 19 regression functions using AST. It does not run that suite. `test_voucher_lookup.py` runs those 19 regression functions. Do not confuse inventory with passing results or claim full specification/security coverage.

## Migration and installation boundary

Use this directory as the single public candidate for extending `gift-card-shopping`; the helper's old internal identifiers are retained to avoid unnecessary engine changes. User-specific reminders, private research history and approval records from local installations are intentionally not exported. Existing private JSON stays outside Git and is not migrated automatically.

After owner approval and repository review, an interactive operator can install the complete skill directory using their agent's supported skill installation workflow. Do not install both this and the earlier standalone draft for the same purpose. This candidate performs no installation or live profile changes. Push, PR, merge and installation are separately authorized actions.

## License

Proposed MIT, consistent with the existing gift-card-shopping procedure and repository license; publication approval is pending. No external site content or real catalog is included.

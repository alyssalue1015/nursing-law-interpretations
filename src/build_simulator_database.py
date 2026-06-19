from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUERY_DB = ROOT / "data" / "nursing_law_interpretations.sqlite"
OUT_DIR = ROOT / "simulator" / "data"
OUT_JSON = OUT_DIR / "simulator_topics.json"
OUT_SOURCES_JSON = OUT_DIR / "simulator_sources.json"
OUT_CSV = OUT_DIR / "simulator_topics.csv"
OUT_DB = OUT_DIR / "nursing_position_simulator.sqlite"
OUT_REVIEW = ROOT / "simulator" / "simulator_topic_review.md"


TOPICS = [
    {
        "id": "T01",
        "name": "護理人員資格與名稱使用",
        "group": "人員資格與執登",
        "keywords": ["護理師", "護士", "名稱", "資格", "證書", "護理"],
        "scenario_triggers": [
            "某人未領有護理師或護士證書卻使用護理名稱",
            "機構或業者使用護理字樣使民眾誤認為護理業務",
        ],
        "position": "先判斷是否具護理師或護士資格，再判斷名稱或服務內容是否使社會大眾誤認為護理人員、護理機構或護理業務。未具資格者不得使用護理師、護士名稱，也不得藉由廣告或職稱混淆法定業務。",
        "decision_questions": [
            "行為人是否領有護理師或護士證書？",
            "使用名稱是否足以使民眾誤認為護理人員或護理業務？",
            "實際服務是否涉及護理人員法第24條業務？",
        ],
        "likely_outputs": [
            "未具資格者使用護理師或護士名稱，傾向認定違反名稱使用限制。",
            "若僅為一般生活服務，但名稱或廣告造成護理業務誤認，仍應依護理人員法及相關規定處理。",
        ],
        "source_ids": ["interp-0008", "interp-0010"],
    },
    {
        "id": "T02",
        "name": "執業登記與執業執照",
        "group": "人員資格與執登",
        "keywords": ["執業登記", "執業執照", "證書", "第8條", "登錄", "執登"],
        "scenario_triggers": [
            "已具護理師證書但未辦執登而執行護理業務",
            "非醫院場域聘用護理人員是否需要執登",
        ],
        "position": "證書代表具備護理人員資格，執業執照才代表可在特定處所執業。只要實際從事護理人員法第24條業務，原則上須向所在地主管機關辦理執業登記並領有執業執照。",
        "decision_questions": [
            "是否已領有護理人員證書？",
            "是否實際執行第24條護理業務？",
            "是否已在該執業所在地辦理執業登記？",
        ],
        "likely_outputs": [
            "僅持有證書但未執登，不足以合法執業。",
            "職稱不影響判斷；實際業務落入第24條時仍須執登。",
        ],
        "source_ids": ["interp-0019", "interp-0039", "interp-0626"],
    },
    {
        "id": "T03",
        "name": "執業處所與其他經中央主管機關認可之機構",
        "group": "人員資格與執登",
        "keywords": ["第12條", "執業處所", "認可之機構", "其他經中央主管機關認可", "場所"],
        "scenario_triggers": [
            "法人、團體或特殊機構想讓護理人員辦理執登",
            "場域不是醫療機構或護理機構，是否可作為執業處所",
        ],
        "position": "護理人員執業處所原則限於醫療機構、護理機構或其他經中央主管機關認可之機構。判斷重點是該場域是否依法應或得配置護理人員，以及該人員是否在該場所實際執行第24條業務。",
        "decision_questions": [
            "該場域是否有法令依據應或得配置護理人員？",
            "是否已由中央主管機關公告或個案認可？",
            "護理人員是否實際在該場域執行護理業務？",
        ],
        "likely_outputs": [
            "依法應或得配置護理人員且實際執行護理業務者，較可能認可作為執業登記場域。",
            "單純衛教、研究或公益任務不必然等於可作為執業登記機構，仍須回到認可條件判斷。",
        ],
        "source_ids": ["interp-0109", "interp-0110", "interp-0620", "interp-0626"],
    },
    {
        "id": "T04",
        "name": "學校護理人員",
        "group": "學校、幼兒園與特殊場域",
        "keywords": ["學校", "校護", "健康中心", "學校衛生", "公共衛生", "衛生教育"],
        "scenario_triggers": [
            "學校護理人員是否屬護理人員法上執業",
            "學校衛生護理人員是否可執行公共衛生業務",
            "健康中心工作是否需要執登",
        ],
        "position": "學校校護工作屬護理人員法第8條所稱執業。學校衛生保健、疾病管理及救護、傳染病防治、預防接種、衛生教育等，屬護理人員業務範疇，也具公共衛生業務性質。",
        "decision_questions": [
            "是否在學校場域擔任校護或健康中心照護工作？",
            "工作內容是否包括衛生保健、疾病管理、救護、傳染病防治、預防接種或衛生教育？",
            "是否依法辦理執業登記？",
        ],
        "likely_outputs": [
            "學校校護不是單純行政職，屬護理執業，應依護理人員法辦理執登及管理。",
            "學校護理人員可依衛生機關工作計畫或公函執行或協助公共衛生業務。",
        ],
        "source_ids": ["interp-0006", "interp-0019", "interp-0039"],
    },
    {
        "id": "T05",
        "name": "學校及幼兒園等教育照護場域",
        "group": "學校、幼兒園與特殊場域",
        "keywords": ["幼兒園", "托嬰中心", "學校", "健康中心", "教育照護", "生活輔導員"],
        "scenario_triggers": [
            "幼兒園、托嬰中心或學校是否可聘護理人員並辦執登",
            "教育照護場域中的健康照護工作是否受護理人員法規範",
        ],
        "position": "幼兒園、托嬰中心、學校健康中心等教育照護場域，如依相關法令得或應配置護理人員，且實際從事第24條業務，傾向要求辦理執業登記。場域不是醫院並不當然免除護理法規。",
        "decision_questions": [
            "該教育照護場域是否依法應或得配置護理人員？",
            "人員是否實際執行第24條業務？",
            "若為支援或代理，是否符合支援報備或事先報准規定？",
        ],
        "likely_outputs": [
            "幼兒園、托嬰中心或學校依法配置護理人員且執行護理業務時，應走執登或支援報備程序。",
            "僅以生活輔導員、保健人員等職稱不能排除實質護理業務判斷。",
        ],
        "source_ids": ["interp-0048", "interp-0039", "interp-0082", "interp-0626"],
    },
    {
        "id": "T06",
        "name": "校護代理、支援與短期請假",
        "group": "學校、幼兒園與特殊場域",
        "keywords": ["校護", "代理", "短時間請假", "支援", "報備", "健康中心"],
        "scenario_triggers": [
            "校護短時間請假，學校找合格但未現職護理人員代理",
            "鄰近機構護理人員支援學校護理工作",
        ],
        "position": "校護短期請假時，仍不能讓未辦執登者直接執業。可商請鄰近機構護理人員依護理人員法第12條支援學校護理工作，並依支援或事先報准程序處理。",
        "decision_questions": [
            "代理者是否具護理人員資格並已合法執業？",
            "支援是否來自鄰近合法執業機構？",
            "是否已依第12條但書完成支援報備或事先報准？",
        ],
        "likely_outputs": [
            "合格但非現職或未執登者，仍不得逕行代理校護執業。",
            "學校短期缺口應優先以合法支援機制處理。",
        ],
        "source_ids": ["interp-0082", "interp-0019"],
    },
    {
        "id": "T07",
        "name": "助產人員、生活輔導員或其他人員支援學校護理工作",
        "group": "學校、幼兒園與特殊場域",
        "keywords": ["助產人員", "生活輔導員", "健康中心", "支援學校", "逾越業務"],
        "scenario_triggers": [
            "僅具助產資格者支援學校護理工作",
            "生活輔導員持護理師證書支援健康中心",
        ],
        "position": "是否可支援學校護理工作，不看職稱而看資格與實際業務。僅具助產資格者執行學校護理工作，因學校護理業務與助產業務不同，可能逾越執業規定。持護理師證書者若到健康中心執行第24條業務，仍須辦理執登。",
        "decision_questions": [
            "該人員具備哪一類醫事人員資格？",
            "實際工作是否為學校護理業務而非原專業法定業務？",
            "若具護理資格，是否已辦理執業登記？",
        ],
        "likely_outputs": [
            "助產人員不得因具醫事資格即支援學校護理工作。",
            "生活輔導員若持護理師證書並執行第24條業務，仍應辦理護理執登。",
        ],
        "source_ids": ["interp-0076", "interp-0039"],
    },
    {
        "id": "T08",
        "name": "護理教育、護理教師與實習指導",
        "group": "學校、幼兒園與特殊場域",
        "keywords": ["護理教師", "護理教育", "實習指導", "護生", "學校為登記處所"],
        "scenario_triggers": [
            "護理教師是否需要執業登記",
            "護理教師兼做護生實習指導是否屬執業",
        ],
        "position": "護理人員擔任護理學校教師，從事護理教育或護生實習指導，若非以執行護理人員業務為職業，可無須辦理執業登記；如欲辦理執登，得以學校為登記處所。",
        "decision_questions": [
            "工作重點是教學與實習指導，還是直接執行護理業務？",
            "是否以執行護理人員法第24條業務為職業？",
            "如需執登，是否以學校所在地為登記處所？",
        ],
        "likely_outputs": [
            "純護理教育或護生實習指導可與校護執業區分。",
            "若教師另直接執行護理業務，仍應回到執登規範判斷。",
        ],
        "source_ids": ["interp-0016", "interp-0086"],
    },
    {
        "id": "T09",
        "name": "醫療輔助行為",
        "group": "醫療輔助行為與專業邊界",
        "keywords": ["醫療輔助", "醫師指示", "第24條", "侵入性", "處置"],
        "scenario_triggers": [
            "護理人員是否可做某項處置",
            "某處置是否屬醫療輔助行為",
        ],
        "position": "醫療輔助行為是護理人員法第24條業務之一，應在醫師指示下行之。判斷新處置時，先看是否影響身體結構、生理機能，是否屬診療照護流程，是否已有特別函釋。",
        "decision_questions": [
            "該行為是否涉及疾病檢查、診斷、治療或照護流程？",
            "是否涉及侵入性檢查、治療、處置或醫療儀器？",
            "是否有醫師指示或監督？",
        ],
        "likely_outputs": [
            "若屬醫療輔助行為，護理人員須在醫師指示下為之。",
            "未具護理資格者不得因有醫囑即執行護理人員法定業務。",
        ],
        "source_ids": ["interp-0039", "interp-0499", "interp-0501"],
    },
    {
        "id": "T10",
        "name": "專科護理師與醫師監督",
        "group": "醫療輔助行為與專業邊界",
        "keywords": ["專科護理師", "醫師監督", "醫療業務", "甄審"],
        "scenario_triggers": [
            "專科護理師是否可執行醫療業務",
            "專科護理師是否取代醫師或其他醫事人員法定業務",
        ],
        "position": "專科護理師可在法定範圍內於醫師監督下執行醫療業務，但不因此取代醫師、助產人員或其他醫事人員法定業務。仍須遵守分科、甄審、監督及執業範圍限制。",
        "decision_questions": [
            "是否具專科護理師資格？",
            "行為是否屬專科護理師依法可於醫師監督下執行之醫療業務？",
            "是否涉及其他醫事人員專屬業務？",
        ],
        "likely_outputs": [
            "專科護理師制度不是醫師或助產人員業務的替代制度。",
            "仍須依醫師監督與相關辦法界定範圍。",
        ],
        "source_ids": ["interp-0612"],
    },
    {
        "id": "T11",
        "name": "非醫事人員與照顧服務員界線",
        "group": "非醫事人員與照顧服務",
        "keywords": ["非醫事人員", "照顧服務員", "看護", "抽痰", "導尿", "鼻胃管"],
        "scenario_triggers": [
            "照顧服務員或看護可否執行抽痰、導尿、管路照護",
            "生活照顧與護理行為如何區分",
        ],
        "position": "生活照顧、清潔、舒適服務可較寬；導尿、抽痰、管路、傷口、造口、腹膜透析導管等涉及護理或醫療專業者，原則嚴格控管。非醫事人員不得執行法定護理或醫療業務。",
        "decision_questions": [
            "行為是否涉及醫療專業判斷或侵入性處置？",
            "是否屬日常生活照顧或維持清潔舒適？",
            "執行者是否具護理人員或其他醫事人員資格？",
        ],
        "likely_outputs": [
            "單純量血壓、脈搏、體溫而未涉及診斷時較可能非醫療業務。",
            "導尿、抽痰、管路更換等通常不能由非醫事人員執行。",
        ],
        "source_ids": ["interp-0504", "interp-0626"],
    },
    {
        "id": "T12",
        "name": "採血、抽動脈血、X光、採檢等具風險處置",
        "group": "醫療輔助行為與專業邊界",
        "keywords": ["採血", "抽動脈血", "X光", "採檢", "咽喉拭子", "COVID"],
        "scenario_triggers": [
            "護理人員是否可執行X光照相、抽動脈血或採檢",
            "新興處置是否可比附既有函釋",
        ],
        "position": "具風險處置應先判斷是否屬醫療輔助行為、是否需醫師指示、是否另有特別法規或函釋。模擬器對新增處置應採保守比附，優先標示需查最新函釋。",
        "decision_questions": [
            "是否已有該處置的專門函釋或公告？",
            "是否屬醫療輔助行為或其他醫事人員專屬業務？",
            "是否在合法機構、合法資格及醫師指示下執行？",
        ],
        "likely_outputs": [
            "如已列於人員執業網頁新函釋，應以新函釋優先於108年彙編。",
            "無明確函釋時，先依醫療輔助行為及專業資格邊界保守判斷。",
        ],
        "source_ids": ["interp-0499", "interp-0614", "interp-0615", "interp-0616"],
    },
    {
        "id": "T13",
        "name": "公共衛生、預防保健與防疫任務",
        "group": "人員資格與執登",
        "keywords": ["公共衛生", "預防保健", "防疫", "傳染病", "衛生教育", "預防接種"],
        "scenario_triggers": [
            "護理人員在學校、衛生機關或計畫中執行公共衛生任務",
            "公共衛生任務是否仍須執登",
        ],
        "position": "公共衛生、預防保健與防疫任務可屬護理人員業務範疇，但仍須回到資格、執登、場域認可與實際業務內容判斷。公共衛生性質不排除護理法規適用。",
        "decision_questions": [
            "任務是否屬預防保健、衛生教育、傳染病防治或預防接種？",
            "執行者是否具護理人員資格並在合法場域執業？",
            "是否由衛生機關工作計畫或公函指派？",
        ],
        "likely_outputs": [
            "學校護理人員可依衛生機關工作計畫或公函協助公共衛生業務。",
            "公共衛生計畫聘用護理人員時，仍須檢視執業登記場域是否合規。",
        ],
        "source_ids": ["interp-0006", "interp-0109", "interp-0110"],
    },
    {
        "id": "T14",
        "name": "支援報備",
        "group": "支援、停歇業、繼續教育",
        "keywords": ["支援", "報備", "事先報准", "跨機構", "第12條"],
        "scenario_triggers": [
            "護理人員跨機構支援是否要事前報准",
            "急救或大量傷病是否可免報備",
        ],
        "position": "跨機構支援原則須事前報准。急救、大量傷病或緊急臨時需求才可能作為例外，且例外應限縮解釋，不宜擴張成常態人力調度。",
        "decision_questions": [
            "是否屬執業機構間支援？",
            "是否跨縣市或跨不同機構？",
            "是否有急救、大量傷病或緊急情況？",
        ],
        "likely_outputs": [
            "一般支援應事前報准或依規定報備。",
            "緊急例外限於臨時增加護理人力協助處理，不適合常態化。",
        ],
        "source_ids": ["interp-0082", "interp-0626"],
    },
    {
        "id": "T15",
        "name": "停業、歇業、復業與執照更新",
        "group": "支援、停歇業、繼續教育",
        "keywords": ["停業", "歇業", "復業", "執照更新", "育嬰假", "繼續教育"],
        "scenario_triggers": [
            "護理人員停業、歇業後復業或更新執照",
            "育嬰假超過一年是否要辦理歇業",
        ],
        "position": "停業、歇業、復業與執照更新皆屬程序性高的執登管理事項。人員暫離執業狀態時，須依停歇業、復業與繼續教育規則處理，不能以實務需求自行跳過。",
        "decision_questions": [
            "是否停業超過法定期間或事實上不再執業？",
            "復業時執照有效期間與繼續教育積分是否符合規定？",
            "是否已向原發照機關報備或申請？",
        ],
        "likely_outputs": [
            "復業或更新執照時，須回到執登及繼續教育辦法判斷。",
            "育嬰假、歇業或退休後再投入工作，不能免除執登程序。",
        ],
        "source_ids": ["interp-0617"],
    },
    {
        "id": "T16",
        "name": "繼續教育、在職教育與公假/工時",
        "group": "支援、停歇業、繼續教育",
        "keywords": ["繼續教育", "在職教育", "公假", "工時", "訓練進修"],
        "scenario_triggers": [
            "醫事人員接受繼續教育是否納入工時或給公假",
            "在職教育費用與差勤如何管理",
        ],
        "position": "近年函釋已將繼續教育與在職教育帶入勞動條件及差勤管理。公務人員可依公務人員請假、訓練進修規定處理；非公務人員則由機構參考並審酌辦理。",
        "decision_questions": [
            "人員是否具公務人員身分？",
            "教育訓練是否與職務有關？",
            "機構是否已有費用補助、差勤或工時管理規範？",
        ],
        "likely_outputs": [
            "與職務相關教育訓練可朝公假或工時管理方向評估。",
            "非公務人員仍可要求機構參考友善在職教育環境原則處理。",
        ],
        "source_ids": ["interp-0617"],
    },
    {
        "id": "T17",
        "name": "勞動條件、調動、休息時間與加班費",
        "group": "勞動條件與執業環境",
        "keywords": ["勞動基準法", "調動", "休息時間", "加班費", "延長工時", "工資"],
        "scenario_triggers": [
            "醫療院所調動護理師工作",
            "護理人員休息時間、延長工時工資爭議",
        ],
        "position": "護理人員雖受護理法規管理，但調動、休息、延長工時工資等仍須回到勞動基準法及勞動部函釋。護理法規不能作為降低勞動保障的理由。",
        "decision_questions": [
            "是否適用勞動基準法？",
            "調動是否符合勞基法第10條之1及相關原則？",
            "延長工時是否依法給付工資？",
        ],
        "likely_outputs": [
            "職場管理問題應同時檢視護理執業規範與勞動法規。",
            "調動、休息時間與加班費爭議，不宜僅以院內管理命令處理。",
        ],
        "source_ids": ["interp-0629"],
    },
    {
        "id": "T18",
        "name": "護病比與人力配置",
        "group": "勞動條件與執業環境",
        "keywords": ["護病比", "三班", "人力配置", "病人安全", "急性一般病床"],
        "scenario_triggers": [
            "醫院護理人力配置是否達標",
            "護病比是否涉及病人安全與執業環境",
        ],
        "position": "護病比與人力配置不是單純內部管理，而是病人安全、執業環境與機構管理議題。遇到類似問題時，應優先查最新公告、評鑑與設置標準。",
        "decision_questions": [
            "該機構或病床類別是否有明確護病比標準？",
            "人力配置是否影響照護品質或病人安全？",
            "是否涉及主管機關督導考核或評鑑？",
        ],
        "likely_outputs": [
            "若已有護病比公告或標準，應以最新標準作為模擬器判準。",
            "人力不足可能連動機構督導、評鑑或勞動條件議題。",
        ],
        "source_ids": ["interp-0630"],
    },
    {
        "id": "T19",
        "name": "護理機構設置、擴充、開業與復業",
        "group": "機構設置與管理",
        "keywords": ["護理機構", "設置", "擴充", "開業", "復業", "遷移", "負責人"],
        "scenario_triggers": [
            "護理機構設置、擴充、遷移或復業",
            "負責人或申請主體變更是否需重新申請",
        ],
        "position": "護理機構設置、開業、遷移、復業與負責人變更，重視許可、登記、實地審查與申請主體是否改變。若涉及個人設置者主體變更，較可能被視為新設立。",
        "decision_questions": [
            "是登記事項變更，還是申請主體變更？",
            "遷移或復業後設施、人員、消防、建管是否仍合格？",
            "是否已依護理機構設置標準及開業程序審查？",
        ],
        "likely_outputs": [
            "復業或遷移原則準用設立規定，但可視原設施與人員是否重大改變簡化程序。",
            "主體變更通常不能只辦登記事項變更。",
        ],
        "source_ids": ["interp-0316", "interp-0317"],
    },
    {
        "id": "T20",
        "name": "護理機構服務對象",
        "group": "機構設置與管理",
        "keywords": ["服務對象", "居家護理", "護理之家", "產後護理", "長期照護"],
        "scenario_triggers": [
            "護理機構是否可收住特定照護需求個案",
            "產後護理機構服務對象是否可放寬",
        ],
        "position": "居家護理、護理之家、產後護理機構等，須依核准服務對象與照護需求判斷。不能任意擴張服務對象，尤其當個案有管路、造口或高護理需求時，應重視照護品質與人力配置。",
        "decision_questions": [
            "該機構類型的法定服務對象為何？",
            "個案照護需求是否超出該機構設置或人力能力？",
            "是否涉及其他主管法規或跨部會權責？",
        ],
        "likely_outputs": [
            "服務對象擴張須有法規依據與照護品質保障。",
            "高護理需求個案不宜僅以機構收住意願判斷。",
        ],
        "source_ids": ["interp-0144"],
    },
    {
        "id": "T21",
        "name": "收費、收據與醫療勞務/生活照顧區分",
        "group": "機構設置與管理",
        "keywords": ["收費", "收據", "醫療勞務", "生活照顧", "產後護理", "尿布", "奶粉"],
        "scenario_triggers": [
            "產後護理機構或護理之家收費項目如何分類",
            "機構是否超收或以其他公司另收費",
        ],
        "position": "護理評估、護理指導、處置偏醫療勞務；尿布、奶粉、清潔用品及一般飲食偏生活照顧。收費項目須清楚、可判別類別、開立收據，且不得超過主管機關核定標準。",
        "decision_questions": [
            "該收費項目屬醫療照護需求衍生，還是一般生活照顧？",
            "是否列入地方主管機關核定收費項目？",
            "收據是否載明服務項目與金額？",
        ],
        "likely_outputs": [
            "未列入核定收費項目的服務，可能構成超收或違規收費。",
            "以商業單位另行收費或推銷，應檢視是否混淆醫療與商業行為。",
        ],
        "source_ids": ["interp-0311"],
    },
    {
        "id": "T22",
        "name": "廣告、名稱與業務包裝",
        "group": "機構設置與管理",
        "keywords": ["廣告", "名稱", "業務項目", "產後護理", "飯店", "美容"],
        "scenario_triggers": [
            "護理機構以休閒飯店、美容服務包裝業務",
            "非護理機構使用護理名稱或宣稱護理服務",
        ],
        "position": "護理機構廣告內容受限，非護理機構不得為護理業務廣告。不得以飯店式、美容式或模糊名稱包裝，使民眾誤認核准業務或醫療護理服務。",
        "decision_questions": [
            "廣告內容是否限於法定可刊登事項？",
            "是否宣傳非核准業務或讓民眾誤認服務性質？",
            "是否涉及非護理機構為護理業務廣告？",
        ],
        "likely_outputs": [
            "強調非核准服務或休閒飯店式服務，可能超出護理機構廣告容許範圍。",
            "美容或SPA使用護理字樣需檢視是否造成護理業務誤認。",
        ],
        "source_ids": ["interp-0164", "interp-0335", "interp-0614"],
    },
    {
        "id": "T23",
        "name": "病歷、紀錄與保密",
        "group": "裁罰、保密與權益保障",
        "keywords": ["紀錄", "病歷", "保密", "個資", "陳情", "秘密"],
        "scenario_triggers": [
            "護理人員執行業務是否需製作紀錄",
            "陳情或照護資料是否可公開",
        ],
        "position": "護理人員執行業務時應製作紀錄；涉及個資、病人資料、陳情內容或業務秘密時，須有保密立場。實習或未取證人員的紀錄亦應由指導護理人員確認。",
        "decision_questions": [
            "是否屬護理人員執行業務產生的紀錄？",
            "資料是否涉及個人隱私、病情、陳情或機密？",
            "未具資格者所作紀錄是否經指導護理人員確認？",
        ],
        "likely_outputs": [
            "護理業務紀錄不能省略，且應依醫療法或相關規定保存。",
            "陳情或個案資料需依保密規定處理。",
        ],
        "source_ids": ["interp-0498", "interp-0501"],
    },
    {
        "id": "T24",
        "name": "違法執業、證照租借與裁罰",
        "group": "裁罰、保密與權益保障",
        "keywords": ["違法執業", "未取得資格", "罰鍰", "證照租借", "裁罰"],
        "scenario_triggers": [
            "未具資格者執行護理業務",
            "機構容留未具資格者擅自執行護理業務",
        ],
        "position": "未具資格執行護理業務、未執登執業、證照租借、機構容留未具資格者，均屬高風險裁罰主題。若涉及刑事責任，應移送檢察機關依法辦理。",
        "decision_questions": [
            "行為人是否具護理人員資格並辦理執登？",
            "是否由雇主或機構容留、指派或默許？",
            "是否涉及證照租借或刑事責任？",
        ],
        "likely_outputs": [
            "未具資格或未執登而執行護理業務，原則傾向違法。",
            "雇主或機構可能與本人同受處罰或負督導責任。",
        ],
        "source_ids": ["interp-0490", "interp-0501"],
    },
    {
        "id": "T25",
        "name": "感染者權益與不得拒絕服務",
        "group": "裁罰、保密與權益保障",
        "keywords": ["愛滋", "感染者", "拒絕服務", "歧視", "長照", "感染管制"],
        "scenario_triggers": [
            "護理機構或長照機構拒收愛滋感染者",
            "因疾病身分差別待遇",
        ],
        "position": "愛滋、傳染病或其他疾病身分不得作為拒絕照護或差別待遇理由。應以正確感染管制、教育訓練與法定照護義務處理，而不是以感染者身分排除服務。",
        "decision_questions": [
            "是否因感染者身分拒絕服務或差別待遇？",
            "是否已有正確感染管制與教育訓練措施？",
            "是否違反長照、感染者權益保障或其他相關法規？",
        ],
        "likely_outputs": [
            "不得因愛滋感染者身分拒絕提供長照或護理相關服務。",
            "主管機關可要求教育訓練並依法查處歧視或拒收情事。",
        ],
        "source_ids": ["interp-0633"],
    },
    {
        "id": "T26",
        "name": "外國人、華僑與境外護理資格",
        "group": "人員資格與執登",
        "keywords": ["外國人", "華僑", "境外資格", "工作證", "外籍看護", "許可"],
        "scenario_triggers": [
            "外國護理資格者可否在我國從事護理工作",
            "外籍看護或care giver可否執行護理工作",
        ],
        "position": "取得外國護理資格不等於可在我國執業。外國人及華僑須依我國法律考試、取得證書、經中央主管機關許可並辦理執業登記，始得執行護理業務。",
        "decision_questions": [
            "是否已依法取得我國護理人員證書？",
            "是否經中央主管機關許可？",
            "是否已辦理執業登記並在合法處所執業？",
        ],
        "likely_outputs": [
            "外國工作證或境外資格本身不足以執行我國護理業務。",
            "外籍看護可做生活照顧，但不能執行法定護理或醫療業務。",
        ],
        "source_ids": ["interp-0504"],
    },
    {
        "id": "T27",
        "name": "護理學生、應屆畢業生與實習護士",
        "group": "人員資格與執登",
        "keywords": ["護理學生", "應屆畢業生", "實習護士", "未取得證書", "指導"],
        "scenario_triggers": [
            "護理應屆畢業生未取得證書前能否執行護理業務",
            "學生或畢業生在護理人員指導下實習的範圍",
        ],
        "position": "未取得證書者原則不得獨立執行護理業務；但在護理人員指導下實習之高級護理職業以上學校學生或畢業生，有特定例外。指導不以現場指導為必要，但所為護理業務應經指導護理人員確認。",
        "decision_questions": [
            "是否為高級護理職業以上學校學生或畢業生？",
            "是否在護理人員指導下執行業務？",
            "是否獨立執行護理業務或紀錄未經確認？",
        ],
        "likely_outputs": [
            "未取證者不得獨立執行護理業務。",
            "符合第37條但書者可在指導下實習，但紀錄與業務須經確認。",
        ],
        "source_ids": ["interp-0488", "interp-0495", "interp-0498", "interp-0501"],
    },
]


def fetch_sources(source_ids: list[str]) -> dict[str, dict]:
    if not QUERY_DB.exists():
        raise FileNotFoundError(f"Missing query database: {QUERY_DB}")

    con = sqlite3.connect(QUERY_DB)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in source_ids)
    rows = con.execute(
        f"""
        select
          id,
          law_name,
          article,
          category,
          issued_date_raw,
          issued_date,
          document_no,
          title,
          start_printed_page,
          end_printed_page,
          start_physical_page,
          end_physical_page,
          source_quality,
          completeness_note,
          body,
          snippet,
          drive_url,
          source_url,
          list_url,
          source_title
        from interpretations
        where id in ({placeholders})
        """,
        source_ids,
    ).fetchall()
    return {row["id"]: dict(row) for row in rows}


def build_outputs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_ids = sorted({source_id for topic in TOPICS for source_id in topic["source_ids"]})
    sources = fetch_sources(source_ids)
    missing = [source_id for source_id in source_ids if source_id not in sources]
    if missing:
        raise RuntimeError(f"Missing source ids in query database: {', '.join(missing)}")

    topics = []
    for topic in TOPICS:
        topic_sources = [sources[source_id] for source_id in topic["source_ids"]]
        topics.append(
            {
                **topic,
                "sources": [
                    {
                        "id": source["id"],
                        "source_title": source["source_title"],
                        "law_name": source["law_name"],
                        "article": source["article"],
                        "category": source["category"],
                        "date": source["issued_date_raw"],
                        "document_no": source["document_no"],
                        "citation_date": citation_date(source),
                        "citation_document_no": citation_document_no(source),
                        "title": source["title"],
                        "printed_page": format_range(source["start_printed_page"], source["end_printed_page"]),
                        "physical_page": format_range(source["start_physical_page"], source["end_physical_page"]),
                        "source_url": source["source_url"],
                        "list_url": source["list_url"],
                        "drive_url": source["drive_url"],
                        "source_quality": source["source_quality"],
                        "excerpt": make_excerpt(source["body"]),
                    }
                    for source in topic_sources
                ],
            }
        )

    metadata = {
        "database_name": "護理立場模擬器資料庫",
        "version": "2026-06-19-draft",
        "purpose": "依護理人員法解釋彙編與衛福部護助e起來法規解釋函，建立可比附既有立場的主題判準資料庫。",
        "status": "draft_for_review",
        "topic_count": len(topics),
        "source_count": len(sources),
        "source_policy": "PDF彙編來源保留日期、發文字號、書上頁碼、PDF實際頁碼與原文摘錄；官方網頁來源保留原文網址、清單來源網址與原文摘錄。",
        "note": "本資料庫獨立於查詢庫，不覆蓋 web/ 或 docs/。後續可接共同來源擷取器定期更新來源後再重建。",
    }

    OUT_JSON.write_text(json.dumps({"metadata": metadata, "topics": topics}, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_SOURCES_JSON.write_text(json.dumps({"metadata": metadata, "sources": sources}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(topics)
    write_sqlite(metadata, topics, sources)
    write_review_markdown(metadata, topics)


def format_range(start, end) -> str:
    if start is None:
        return ""
    if end is None or end == start:
        return str(start)
    return f"{start}-{end}"


def make_excerpt(body: str, limit: int = 900) -> str:
    text = " ".join((body or "").split())
    return text[:limit]


def citation_date(source: dict) -> str:
    body = source.get("body") or ""
    match = re.search(r"發文日期[:：]\s*中華民國\s*([0-9]+年[0-9]+月[0-9]+日)", body)
    if match:
        return match.group(1)
    return source.get("issued_date_raw") or ""


def citation_document_no(source: dict) -> str:
    if source.get("document_no"):
        return source["document_no"]
    body = source.get("body") or ""
    match = re.search(r"發文字號[:：]\s*([^\n\r ]+)", body)
    if match:
        return match.group(1)
    return ""


def write_csv(topics: list[dict]) -> None:
    fieldnames = [
        "id",
        "name",
        "group",
        "keywords",
        "position",
        "decision_questions",
        "likely_outputs",
        "source_ids",
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for topic in topics:
            writer.writerow(
                {
                    "id": topic["id"],
                    "name": topic["name"],
                    "group": topic["group"],
                    "keywords": "、".join(topic["keywords"]),
                    "position": topic["position"],
                    "decision_questions": "；".join(topic["decision_questions"]),
                    "likely_outputs": "；".join(topic["likely_outputs"]),
                    "source_ids": "、".join(topic["source_ids"]),
                }
            )


def write_sqlite(metadata: dict, topics: list[dict], sources: dict[str, dict]) -> None:
    if OUT_DB.exists():
        OUT_DB.unlink()
    con = sqlite3.connect(OUT_DB)
    con.execute(
        """
        create table metadata (
          key text primary key,
          value text
        )
        """
    )
    con.execute(
        """
        create table topics (
          id text primary key,
          name text not null,
          topic_group text not null,
          keywords text not null,
          scenario_triggers text not null,
          position text not null,
          decision_questions text not null,
          likely_outputs text not null
        )
        """
    )
    con.execute(
        """
        create table sources (
          id text primary key,
          source_title text,
          law_name text,
          article text,
          category text,
          issued_date_raw text,
          issued_date text,
          document_no text,
          title text,
          citation_date text,
          citation_document_no text,
          start_printed_page integer,
          end_printed_page integer,
          start_physical_page integer,
          end_physical_page integer,
          source_quality text,
          completeness_note text,
          body text,
          snippet text,
          drive_url text,
          source_url text,
          list_url text
        )
        """
    )
    con.execute(
        """
        create table topic_sources (
          topic_id text not null,
          source_id text not null,
          primary key (topic_id, source_id)
        )
        """
    )
    con.executemany("insert into metadata(key, value) values (?, ?)", [(key, json.dumps(value, ensure_ascii=False)) for key, value in metadata.items()])
    con.executemany(
        """
        insert into topics values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                topic["id"],
                topic["name"],
                topic["group"],
                json.dumps(topic["keywords"], ensure_ascii=False),
                json.dumps(topic["scenario_triggers"], ensure_ascii=False),
                topic["position"],
                json.dumps(topic["decision_questions"], ensure_ascii=False),
                json.dumps(topic["likely_outputs"], ensure_ascii=False),
            )
            for topic in topics
        ],
    )
    con.executemany(
        """
        insert into sources values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                source["id"],
                source["source_title"],
                source["law_name"],
                source["article"],
                source["category"],
                source["issued_date_raw"],
                source["issued_date"],
                source["document_no"],
                source["title"],
                citation_date(source),
                citation_document_no(source),
                source["start_printed_page"],
                source["end_printed_page"],
                source["start_physical_page"],
                source["end_physical_page"],
                source["source_quality"],
                source["completeness_note"],
                source["body"],
                source["snippet"],
                source["drive_url"],
                source["source_url"],
                source["list_url"],
            )
            for source in sources.values()
        ],
    )
    con.executemany(
        "insert into topic_sources(topic_id, source_id) values (?, ?)",
        [(topic["id"], source_id) for topic in topics for source_id in topic["source_ids"]],
    )
    con.commit()
    con.close()


def write_review_markdown(metadata: dict, topics: list[dict]) -> None:
    lines = [
        "# 護理立場模擬器主題審核表",
        "",
        f"- 版本：{metadata['version']}",
        f"- 狀態：{metadata['status']}",
        f"- 主題數：{metadata['topic_count']}",
        f"- 代表來源數：{metadata['source_count']}",
        "",
        "## 審核重點",
        "",
        "請先確認每個主題是否要保留、合併、拆分或改名，再確認「可形成的模擬器立場」是否符合你的工作用途。",
        "",
    ]

    current_group = None
    for topic in topics:
        if topic["group"] != current_group:
            current_group = topic["group"]
            lines.extend(["", f"## {current_group}", ""])

        lines.extend(
            [
                f"### {topic['id']} {topic['name']}",
                "",
                f"**關鍵字**：{'、'.join(topic['keywords'])}",
                "",
                f"**可形成的模擬器立場**：{topic['position']}",
                "",
                "**適用情境**：",
                "",
            ]
        )
        for item in topic["scenario_triggers"]:
            lines.append(f"- {item}")

        lines.extend(["", "**判斷問題**：", ""])
        for item in topic["decision_questions"]:
            lines.append(f"- {item}")

        lines.extend(["", "**可能結論**：", ""])
        for item in topic["likely_outputs"]:
            lines.append(f"- {item}")

        lines.extend(["", "**代表來源**：", ""])
        if topic["sources"]:
            for source in topic["sources"]:
                citation = source["citation_document_no"] or source["document_no"] or "字號待補"
                date = source["citation_date"] or source["date"] or "日期待補"
                page_bits = []
                if source["printed_page"]:
                    page_bits.append(f"書上頁碼 {source['printed_page']}")
                if source["physical_page"]:
                    page_bits.append(f"PDF頁碼 {source['physical_page']}")
                if source["source_url"]:
                    page_bits.append(f"原文網址 {source['source_url']}")
                page_text = "；".join(page_bits) if page_bits else "頁碼/網址待補"
                lines.append(f"- {date}，{citation}，{source['title']}（{page_text}）")
        else:
            lines.append("- 待補代表來源")

        lines.extend(["", "**來源摘錄檢查**：", ""])
        if topic["sources"]:
            for source in topic["sources"]:
                lines.append(f"> {source['excerpt'][:360]}")
                lines.append("")
        else:
            lines.append("> 待補")
            lines.append("")

    OUT_REVIEW.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_outputs()

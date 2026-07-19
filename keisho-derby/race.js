const canvas = document.querySelector("#raceCanvas");
const ctx = canvas.getContext("2d");
const LOGICAL_WIDTH = 360;
const RENDER_SCALE = 2;
let logicalHeight = 500;
function configureCanvas(height){
  logicalHeight=height;
  canvas.width=LOGICAL_WIDTH*RENDER_SCALE;
  canvas.height=height*RENDER_SCALE;
  ctx.setTransform(RENDER_SCALE,0,0,RENDER_SCALE,0,0);
  ctx.imageSmoothingEnabled=false;
}
configureCanvas(logicalHeight);

const remainingEl = document.querySelector("#remaining");
const raceTimeEl = document.querySelector("#raceTime");
const split1000El = document.querySelector("#split1000");
const finishTimeEl = document.querySelector("#finishTime");
const phaseEl = document.querySelector("#phase");
const paceDisplayEl = document.querySelector("#paceDisplay");
const slopeStateEl = document.querySelector("#slopeState");
const elevationHorsesEl = document.querySelector("#elevationHorses");
const elevationPathEl = document.querySelector("#elevationPath");
const commentaryEl = document.querySelector("#commentary");
const rankingEl = document.querySelector("#ranking");
const startButton = document.querySelector("#startButton");
const pauseButton = document.querySelector("#pauseButton");
const speedButton = document.querySelector("#speedButton");
const resetButton = document.querySelector("#resetButton");
const gateSkipButton = document.querySelector("#gateSkipButton");
const raceTestBackButton = document.querySelector("#raceTestBackButton");
const winnerPopup = document.querySelector("#winnerPopup");
const benchmarkTimesEl = document.querySelector("#benchmarkTimes");
const weatherDisplayEl = document.querySelector("#weatherDisplay");
const winnerReplayButton = document.querySelector("#winnerReplayButton");
const favoriteRaceButton = document.querySelector("#favoriteRaceButton");
const showResultButton = document.querySelector("#showResultButton");

// JRAの枠色：1白、2黒、3赤、4青、5黄、6緑、7橙、8桃
const COLORS = ["#f5f3e8", "#151515", "#d93732", "#2879d8", "#efc52d", "#36a852", "#e87822", "#ec73ad"];
const RIVAL_CATALOG = [
  {name:"サクラバクシンオー",surface:"芝",min:1000,max:1400,style:"先行",trait:"speed"},{name:"ロードカナロア",surface:"芝",min:1200,max:1600,style:"先行",trait:"steady"},
  {name:"カルストンライトオ",surface:"芝",min:1000,max:1200,style:"逃げ",trait:"straight"},{name:"デュランダル",surface:"芝",min:1200,max:1600,style:"追込",trait:"kick"},
  {name:"ビリーヴ",surface:"芝",min:1000,max:1400,style:"先行",trait:"steady"},{name:"ニシノフラワー",surface:"芝",min:1200,max:1600,style:"先行",trait:"early"},
  {name:"タイキシャトル",surface:"芝",min:1200,max:1600,style:"先行",trait:"steady"},{name:"ニホンピロウイナー",surface:"芝",min:1400,max:1600,style:"先行",trait:"mile"},
  {name:"ノースフライト",surface:"芝",min:1400,max:1800,style:"差し",trait:"kick"},{name:"ダイワメジャー",surface:"芝",min:1600,max:2000,style:"先行",trait:"power"},
  {name:"モーリス",surface:"芝",min:1600,max:2000,style:"先行",trait:"late"},{name:"グランアレグリア",surface:"芝",min:1200,max:2000,style:"差し",trait:"kick"},
  {name:"ウオッカ",surface:"芝",min:1600,max:2400,style:"差し",trait:"tokyo"},{name:"シンボリルドルフ",surface:"芝",min:2000,max:3000,style:"先行",trait:"steady"},
  {name:"トウカイテイオー",surface:"芝",min:2000,max:2500,style:"先行",trait:"fragile"},{name:"テイエムオペラオー",surface:"芝",min:2000,max:3200,style:"先行",trait:"guts"},
  {name:"サイレンススズカ",surface:"芝",min:1800,max:2200,style:"大逃げ",trait:"speed"},{name:"エアグルーヴ",surface:"芝",min:1800,max:2400,style:"先行",trait:"steady"},
  {name:"ジェンティルドンナ",surface:"芝",min:2000,max:2400,style:"先行",trait:"power"},{name:"ブエナビスタ",surface:"芝",min:1600,max:2400,style:"差し",trait:"steady"},
  {name:"ディープインパクト",surface:"芝",min:2000,max:3200,style:"追込",trait:"kick"},{name:"ナリタブライアン",surface:"芝",min:2000,max:3000,style:"先行",trait:"power"},
  {name:"オルフェーヴル",surface:"芝",min:2000,max:3200,style:"差し",trait:"wild"},{name:"スペシャルウィーク",surface:"芝",min:2000,max:3200,style:"差し",trait:"steady"},
  {name:"メジロマックイーン",surface:"芝",min:2400,max:3200,style:"先行",trait:"stamina"},{name:"ライスシャワー",surface:"芝",min:2400,max:3200,style:"差し",trait:"stamina"},
  {name:"ゴールドシップ",surface:"芝",min:2000,max:3200,style:"まくり",trait:"wild"},{name:"キタサンブラック",surface:"芝",min:2000,max:3200,style:"逃げ",trait:"stamina"},
  {name:"オグリキャップ",surface:"芝",min:1600,max:2500,style:"先行",trait:"guts"},{name:"ハイセイコー",surface:"芝",min:1600,max:2400,style:"先行",trait:"power"},
  {name:"コスモバルク",surface:"芝",min:1800,max:2400,style:"先行",trait:"wild"},
  {name:"サウスヴィグラス",surface:"ダート",min:1000,max:1400,style:"先行",trait:"speed"},{name:"ブロードアピール",surface:"ダート",min:1200,max:1400,style:"追込",trait:"kick"},
  {name:"メイショウボーラー",surface:"ダート",min:1200,max:1600,style:"逃げ",trait:"speed"},{name:"ブルーコンコルド",surface:"ダート",min:1400,max:1600,style:"差し",trait:"local"},
  {name:"ラブミーチャン",surface:"ダート",min:800,max:1400,style:"逃げ",trait:"speed"},{name:"クロフネ",surface:"ダート",min:1600,max:2100,style:"先行",trait:"power"},
  {name:"アドマイヤドン",surface:"ダート",min:1600,max:2000,style:"先行",trait:"steady"},{name:"カネヒキリ",surface:"ダート",min:1600,max:2100,style:"差し",trait:"guts"},
  {name:"ゴールドアリュール",surface:"ダート",min:1600,max:2000,style:"先行",trait:"steady"},{name:"エスポワールシチー",surface:"ダート",min:1600,max:1800,style:"逃げ",trait:"local"},
  {name:"トランセンド",surface:"ダート",min:1600,max:1800,style:"逃げ",trait:"pace"},{name:"メイセイオペラ",surface:"ダート",min:1600,max:2000,style:"先行",trait:"local"},
  {name:"ホクトベガ",surface:"ダート",min:1800,max:2400,style:"先行",trait:"power"},{name:"アブクマポーロ",surface:"ダート",min:1800,max:2400,style:"先行",trait:"local"},
  {name:"スマートファルコン",surface:"ダート",min:1800,max:2100,style:"逃げ",trait:"speed"},{name:"ヴァーミリアン",surface:"ダート",min:1800,max:2500,style:"差し",trait:"steady"},
  {name:"コパノリッキー",surface:"ダート",min:1600,max:2000,style:"逃げ",trait:"wild"},{name:"ホッコータルマエ",surface:"ダート",min:1800,max:2100,style:"先行",trait:"steady"},
  {name:"フリオーソ",surface:"ダート",min:1600,max:2400,style:"先行",trait:"local"},{name:"ワンダーアキュート",surface:"ダート",min:1800,max:2100,style:"差し",trait:"late"},
  {name:"アジュディミツオー",surface:"ダート",min:1600,max:2400,style:"先行",trait:"local"},{name:"トーシンブリザード",surface:"ダート",min:1400,max:2100,style:"先行",trait:"local"},
  {name:"ロジータ",surface:"ダート",min:1600,max:2400,style:"先行",trait:"power"},{name:"フジノウェーブ",surface:"ダート",min:1200,max:1600,style:"差し",trait:"local"},
  {name:"ボンネビルレコード",surface:"ダート",min:1600,max:2400,style:"差し",trait:"late"},{name:"トウケイニセイ",surface:"ダート",min:1600,max:2200,style:"先行",trait:"steady"}
];
const FICTIONAL_PREFIXES=["ドット","ピクセル","レトロ","メモリー","サンライズ","ムーン","スター","グランド","ブルー","レッド","シルバー","ゴールド","チェリー","ミント","コスモ","ライト","ノーブル","ブレイブ","ハッピー","ミラクル"];
const FICTIONAL_SUFFIXES=["ロード","ベル","ランナー","アロー","ギア","ボルト","ミスト","リボン","ハート","エース","キング","クイーン","ソング","フラッシュ","ステップ","リーフ","ウイング","バード","ストーム","ウェーブ"];
const FICTIONAL_RIVALS=Array.from({length:160},(_,i)=>{
  const surface=i%3===0?"ダート":"芝",band=i%4;
  const ranges=[[1000,1400],[1400,1800],[1800,2200],[2200,3200]][band];
  return{name:`${FICTIONAL_PREFIXES[i%FICTIONAL_PREFIXES.length]}${FICTIONAL_SUFFIXES[(i*7+Math.floor(i/20))%FICTIONAL_SUFFIXES.length]}`,
    surface,min:ranges[0],max:ranges[1],style:["逃げ","先行","差し","追込"][i%4],trait:i%11===0?"steady":i%13===0?"power":null,fictional:true};
});
const STYLE_PATTERNS = [
  ["逃げ", "先行", "差し", "先行", "差し", "追込", "差し", "追込"],
  ["逃げ", "逃げ", "先行", "先行", "差し", "差し", "追込", "追込"],
  ["逃げ", "逃げ", "逃げ", "先行", "差し", "差し", "追込", "追込"],
  ["逃げ", "先行", "先行", "先行", "差し", "差し", "差し", "追込"],
];
let TOTAL = 2400;
// The finish line is fixed. Each start is calculated backwards from the
// official lap length, so different distances no longer share one start.
let LAP = 2083.1;
let FINISH_PROGRESS = .24;
let START_PROGRESS = FINISH_PROGRESS - TOTAL / LAP;
// 東京芝2400mを約2分24秒で走破する基礎速度。
// 2:20.3のコースレコードから通常のダービー水準2:23〜2:26を想定。
let BASE_PROGRESS_PER_MS = (TOTAL / LAP) / 144000;

let horses = [];
let state = "ready";
let multiplier = 1;
let lastTime = 0;
let raceClock = 0;
let preRaceClock = 0;
let weatherClock = 0;
let waitingMotionClock = 0;
let gateDifficultHorseId = null;
let cheerClock = 0;
let commentaryStamp = new Set();
let commentaryHistory = [];
let gateStartTimer = 0;
let raf = 0;
let racePace = { name: "平均", escapeCount: 1, timeFactor: 1 };
let split1000Time = null;
let measuredPace = "未確定";
let raceSurface = "芝";
let currentRaceVenue = "東京";
let raceDirectionOverride = null;
let currentCourseSpec = {route:"",lap:2083.1,straight:525.9,elevation:2.7};
let opponentAbilities = [];
let opponentNames = [];
let opponentRivals = [];
let fieldAverageAbility = 920;
let raceSeed = 1;
let randomState = 1;
let simulationAccumulator = 0;
let resultDispatchedForRace = false;
let pendingResultDetail = null;
let archiveReplay = false;
let horizontalLayout = false;
let layoutV2 = false;
let courseAuditMode = false;
let drawingCourseTrace = false;
// スタンド下配置を本編でも共通使用。走路はスタンドに近づけつつ接触させない。
const COURSE_Y_SHIFT = 6;
let playerNumber = 1;
let visionRanks = new Map();
let visionRankStamp = 0;
const COURSE_PATH_CACHE=new WeakMap();
// 「通常」を従来シミュレーションの4倍速として扱う。
// 画面表示の2倍・4倍は通常速度を基準に、それぞれ内部8倍・16倍になる。
const BASE_PLAYBACK_RATE = 4;
const PLAYBACK_RATES=[1,2,4];
let playerSetup = { horseName: "ドットスター", ability: 940, dash: 550, gateSkill:450, condition: 60, fatigue: 10, difficulty: 840, heavyTrack:500, temperament:"普通",temperamentValue:50,equippedTack:null,weather:"晴", going:"良", baseTime: 144000 };

function setCommentary(message,reset=false){
  if(reset)commentaryHistory=[];
  if(!message)return;
  if(commentaryHistory[commentaryHistory.length-1]!==message)commentaryHistory.push(message);
  commentaryHistory=commentaryHistory.slice(-4);
  commentaryEl.textContent=commentaryHistory.join("\n");
}
function wrappedCommentaryLines(messages,maxChars=28){
  return messages.flatMap(message=>{
    const chars=Array.from(message),lines=[];
    for(let i=0;i<chars.length;i+=maxChars)lines.push(chars.slice(i,i+maxChars).join(""));
    return lines.length?lines:[""];
  }).slice(-4);
}

function raceRandom() {
  randomState = (randomState * 1664525 + 1013904223) >>> 0;
  return randomState / 4294967296;
}

// JRA公式コースデータを画面用の比率へ変換した全10場プロファイル。
const TRACK_PROFILES={
  "札幌":{turn:"右",straight:266,elevation:.7,straightShare:.28,roundness:1.10,facility:"city",innerBias:.010,frontBias:.011},
  "函館":{turn:"右",straight:262,elevation:3.5,straightShare:.27,roundness:1.00,facility:"sea",innerBias:.012,frontBias:.012},
  "福島":{turn:"右",straight:292,elevation:1.9,straightShare:.29,roundness:.92,facility:"fkc",innerBias:.013,frontBias:.012},
  "新潟":{turn:"左",straight:659,elevation:2.2,straightShare:.41,roundness:1.18,facility:"long",innerBias:.002,frontBias:-.006},
  "東京":{turn:"左",straight:526,elevation:2.7,straightShare:.34,roundness:1.14,facility:"museum",innerBias:.004,frontBias:-.003},
  "中山":{turn:"右",straight:310,elevation:5.3,straightShare:.29,roundness:.84,facility:"garden",innerBias:.012,frontBias:.010},
  "中京":{turn:"左",straight:413,elevation:3.5,straightShare:.32,roundness:.96,facility:"stage",innerBias:.006,frontBias:-.001},
  "京都":{turn:"右",straight:404,elevation:4.3,straightShare:.32,roundness:1.04,facility:"pond",innerBias:.006,frontBias:.002},
  "阪神":{turn:"右",straight:474,elevation:2.4,straightShare:.35,roundness:1.10,facility:"terrace",innerBias:.004,frontBias:-.002},
  "小倉":{turn:"右",straight:293,elevation:3.0,straightShare:.29,roundness:.90,facility:"garden",innerBias:.014,frontBias:.013},
  "門別":{turn:"右",straight:330,elevation:1.54,straightShare:.30,roundness:1.04,facility:"north",innerBias:.009,frontBias:.004},
  "盛岡":{turn:"左",straight:300,elevation:4.4,straightShare:.30,roundness:1.06,facility:"hill",innerBias:.007,frontBias:.001},
  "水沢":{turn:"右",straight:245,elevation:0,straightShare:.25,roundness:.78,facility:"garden",innerBias:.017,frontBias:.018},
  "浦和":{turn:"左",straight:220,elevation:0,straightShare:.25,roundness:.78,facility:"city",innerBias:.018,frontBias:.019},
  "船橋":{turn:"左",straight:308,elevation:0,straightShare:.30,roundness:.94,facility:"city",innerBias:.010,frontBias:.006},
  "大井":{turn:"右",straight:386,elevation:0,straightShare:.32,roundness:1.04,facility:"city",innerBias:.005,frontBias:-.002},
  "川崎":{turn:"左",straight:300,elevation:0,straightShare:.29,roundness:.80,facility:"city",innerBias:.016,frontBias:.016},
  "金沢":{turn:"右",straight:236,elevation:0,straightShare:.25,roundness:.79,facility:"garden",innerBias:.017,frontBias:.018},
  "笠松":{turn:"右",straight:201,elevation:1.92,straightShare:.23,roundness:.70,facility:"river",innerBias:.020,frontBias:.021},
  "名古屋":{turn:"右",straight:240,elevation:0,straightShare:.26,roundness:.77,facility:"city",innerBias:.017,frontBias:.017},
  "園田":{turn:"右",straight:213,elevation:1.23,straightShare:.24,roundness:.72,facility:"city",innerBias:.020,frontBias:.021},
  "姫路":{turn:"右",straight:230,elevation:0,straightShare:.25,roundness:.78,facility:"castle",innerBias:.018,frontBias:.019},
  "高知":{turn:"右",straight:200,elevation:1.58,straightShare:.24,roundness:.75,facility:"hill",innerBias:-.004,frontBias:.018},
  "佐賀":{turn:"右",straight:200,elevation:1.0,straightShare:.24,roundness:.75,facility:"garden",innerBias:.018,frontBias:.019},
  "帯広":{turn:"直線",straight:200,elevation:1.6,straightShare:1,roundness:0,facility:"banei",innerBias:0,frontBias:0},
};
function trackProfile(){
  const base=TRACK_PROFILES[currentRaceVenue]||TRACK_PROFILES["東京"];
  const official=window.COURSE_LAYOUTS?.[currentRaceVenue];
  const route=currentCourseSpec.route;
  const direction=raceDirectionOverride||official?.direction;
  const officialTurn=direction==="right"?"右":direction==="left"?"左":base.turn;
  return {...base,turn:officialTurn,straight:currentCourseSpec.straight??base.straight,elevation:currentCourseSpec.elevation??base.elevation,
    straightShare:route==="外回り"?Math.max(base.straightShare,.36):route==="内回り"?Math.min(base.straightShare,.30):base.straightShare,
    roundness:route==="外回り"?base.roundness*1.08:route==="内回り"?base.roundness*.94:base.roundness};
}
// JRA course lap lengths (metres). Turf uses the rail/course normally used by
// the races currently in the prototype (e.g. Hanshin 1800m = outer course).
const COURSE_LAPS = {
  "札幌": { "芝": 1640.9, "ダート": 1487.0 },
  "函館": { "芝": 1626.6, "ダート": 1475.8 },
  "福島": { "芝": 1600.0, "ダート": 1444.6 },
  "新潟": { "芝": 2223.0, "ダート": 1472.5 },
  "東京": { "芝": 2083.1, "ダート": 1899.0 },
  "中山": { "芝": 1667.1, "ダート": 1493.0 },
  "中京": { "芝": 1705.9, "ダート": 1530.0 },
  "京都": { "芝": 1894.3, "ダート": 1607.6 },
  "阪神": { "芝": 2089.0, "ダート": 1517.6 },
  "小倉": { "芝": 1615.1, "ダート": 1445.4 },
  "門別": { "ダート": 1600 },
  "盛岡": { "芝": 1400, "ダート": 1600 },
  "浦和": { "ダート": 1200 },
  "船橋": { "ダート": 1400 },
  "大井": { "ダート": 1600 },
  "川崎": { "ダート": 1200 },
  "金沢": { "ダート": 1200 },
  "名古屋": { "ダート": 1180 },
  "園田": { "ダート": 1051 },
  "高知": { "ダート": 1100 },
  "佐賀": { "ダート": 1100 },
};
// JRA公式コースデータ（Aコース）に基づく、距離別の内・外回り。
// 混合はスタート後に外回りから内回りへ合流する長距離専用形態。
const TURF_ROUTE_BY_DISTANCE={
  "新潟":{1000:"直線",1200:"内回り",1400:"外回り",1600:"外回り",1800:"外回り",2000:"外回り",2200:"内回り",2400:"内回り",3000:"外回り",3200:"外回り"},
  "中山":{1200:"外回り",1600:"外回り",1800:"内回り",2000:"内回り",2200:"外回り",2500:"内回り",2600:"外回り",3200:"外→内",3600:"内回り",4000:"外回り"},
  "京都":{1100:"内回り",1200:"内回り",1400:"外回り",1600:"外回り",1800:"外回り",2000:"内回り",2200:"外回り",2400:"外回り",3000:"外回り",3200:"外回り"},
  "阪神":{1200:"内回り",1400:"内回り",1600:"外回り",1800:"外回り",2000:"内回り",2200:"内回り",2400:"外回り",2600:"外回り",3000:"内回り",3200:"外→内"}
};
const TURF_ROUTE_SPECS={
  "新潟":{内回り:{lap:1623,straight:358.7,elevation:.8},外回り:{lap:2223,straight:658.7,elevation:2.2},直線:{lap:1000,straight:1000,elevation:0}},
  "中山":{内回り:{lap:1667.1,straight:310,elevation:5.3},外回り:{lap:1839.7,straight:310,elevation:5.3},"外→内":{lap:1667.1,straight:310,elevation:5.3}},
  "京都":{内回り:{lap:1782.8,straight:328.4,elevation:3.1},外回り:{lap:1894.3,straight:403.7,elevation:4.3}},
  "阪神":{内回り:{lap:1689,straight:356.5,elevation:1.9},外回り:{lap:2089,straight:473.6,elevation:2.4},"外→内":{lap:1689,straight:356.5,elevation:2.4}}
};
function courseSpec(){
  const official=window.COURSE_LAYOUTS?.[currentRaceVenue];
  if(currentRaceVenue==="帯広")return{route:"直線",layoutKey:"banei",lap:200,straight:200,elevation:1.6};
  const route=raceSurface==="芝"?TURF_ROUTE_BY_DISTANCE[currentRaceVenue]?.[TOTAL]:"ダート";
  const routed=route&&TURF_ROUTE_SPECS[currentRaceVenue]?.[route];
  const profile=TRACK_PROFILES[currentRaceVenue]||TRACK_PROFILES["東京"];
  const lap=(COURSE_LAPS[currentRaceVenue]||COURSE_LAPS["東京"])[raceSurface]||2083.1;
  if(routed){
    const layoutKey=route.includes("外")?"turf_outer":route.includes("内")?"turf_inner":"turf";
    return{route,layoutKey,...routed};
  }
  if(official){
    const surface=raceSurface==="芝"?"turf":"dirt";
    const keys=Object.keys(official.layouts).filter(k=>k.startsWith(surface));
    const layoutKey=keys.includes(surface)?surface:keys.includes(`${surface}_outer`)?`${surface}_outer`:keys[0];
    return{route:route||raceSurface,layoutKey,lap:official.lap[layoutKey]||official.lap[surface]||lap,
      straight:official.straight[layoutKey]||official.straight[surface]||profile.straight,elevation:official.elevation};
  }
  return{route:route||raceSurface,layoutKey:raceSurface==="芝"?"turf":"dirt",lap,straight:profile.straight,elevation:profile.elevation};
}
function configureCourseDistance(){
  currentCourseSpec=courseSpec();
  LAP=currentCourseSpec.lap;
  // 決勝線は各場のホーム直線内（スタンド前）に置く。
  // 固定値だと直線割合の短い競馬場でコーナーへ入るため、コース形状ごとに算出する。
  const profile=trackProfile();
  const renderedFinish=window.COURSE_LAYOUTS?.[currentRaceVenue]?.finishProgress??Math.max(.14,Math.min(profile.straightShare-.025,profile.straightShare*.72));
  // スタンド下レイアウトでは中心線の基準点を決勝線に固定する。
  FINISH_PROGRESS=renderedFinish;
  START_PROGRESS=FINISH_PROGRESS-TOTAL/LAP;
}
function finishMarkerVisible(){
  if(TOTAL<=LAP)return true;
  const leader=order()[0];
  if(!leader)return false;
  // 長距離戦では途中のゴール板をゴールと誤認しないよう、最終周に入ってから表示する。
  return raceDistance(leader)>=Math.max(0,TOTAL-LAP)-2;
}
function startMarkerVisible(){return ["ready","parade","gates","gateBreak"].includes(state)}
function trackBiasFor(number,style){
  const profile=trackProfile();
  if(currentRaceVenue==="新潟"&&raceSurface==="芝"&&TOTAL===1000){
    // 新潟芝直線1000mは外枠ほど進路を取りやすい傾向を再現する。
    return 1+(number-4.5)*.006;
  }
  const shortFactor=TOTAL<=1400?1.35:TOTAL<=1800?1.12:TOTAL>=2400?.72:1;
  const dirtFactor=raceSurface==="ダート"?1.18:1;
  const insideScore=(4.5-number)/3.5;
  const styleScore=style==="逃げ"?1:style==="先行"?.55:style==="差し"?-.35:-.75;
  return 1+profile.innerBias*insideScore*shortFactor*dirtFactor+profile.frontBias*styleScore*shortFactor;
}
function trackBiasLabel(){
  const profile=trackProfile();
  if(currentRaceVenue==="新潟"&&raceSurface==="芝"&&TOTAL===1000)return "外枠有利・直線競馬";
  const frame=profile.innerBias>=.011?"内枠有利":profile.innerBias<=.003?"枠差小":"やや内枠向き";
  const run=profile.frontBias>=.009?"前有利":profile.frontBias<=-.004?"差し向き":"脚質差小";
  return `${frame}・${run}`;
}

function makeHorse(i, styles) {
  const isPlayer = i === playerNumber-1;
  const opponentIndex=i-(i>playerNumber-1?1:0);
  const baseOpponentAbility = opponentAbilities[opponentIndex] ?? playerSetup.ability;
  const rival=opponentRivals[opponentIndex]||null;
  const opponentAbility=baseOpponentAbility+(rival?.legend?(playerSetup.raceClass==="G1"?22:14):0);
  const listedStyle=rival?.style||styles[i];
  const resolvedStyle=listedStyle==="大逃げ"?"逃げ":listedStyle==="まくり"?"差し":listedStyle;
  const effectiveStyle=isPlayer?styles[i]:resolvedStyle;
  const dashBonus=rival?.trait==="speed"?65:rival?.trait==="power"?25:0;
  const temperament=rival?.trait==="wild"?78:rival?.trait==="steady"?32:35+Math.round(raceRandom()*45);
  return {
    id: i + 1,
    name: isPlayer ? playerSetup.horseName : rival?.name||opponentNames[opponentIndex],
    color: COLORS[i],
    style: effectiveStyle,
    styleLabel:isPlayer?styles[i]:listedStyle,
    rivalTrait:rival?.trait||null,
    progress: START_PROGRESS - i * .0009,
    // 基本は内ラチ沿い。逃げ・先行ほど内、差し・追込も道中は馬群内で脚をためる。
    lane: effectiveStyle === "逃げ" ? 7.25 : effectiveStyle === "先行" ? 6.45 - (i % 2) * .35 : 5.75 - (i % 3) * .35,
    targetLane: effectiveStyle === "逃げ" ? 7.25 : effectiveStyle === "先行" ? 6.45 - (i % 2) * .35 : 5.75 - (i % 3) * .35,
    stamina: 1,
    ability: isPlayer ? playerSetup.ability : opponentAbility,
    heavyTrack: isPlayer ? playerSetup.heavyTrack : 400 + Math.round(raceRandom()*350),
    dash: isPlayer ? playerSetup.dash : 460 + ((i * 70) % 200)+dashBonus,
    gateSkill:isPlayer?playerSetup.gateSkill:380+Math.round(raceRandom()*280),
    // プレイヤーの馬体・調子・疲労は実戦能力へ反映済み。
    // ここでは全馬共通の小さな当日変動だけを加える。
    condition: isPlayer
      ? .975 + Math.max(0,Math.min(100,playerSetup.condition))*.00032 + (raceRandom()-.5)*.006
      : .992 + raceRandom() * .016,
    speed: 1,
    odds: 0,
    popularity: 0,
    trouble: raceRandom(),
    temperamentValue:isPlayer?playerSetup.temperamentValue:temperament,
    equippedTack:isPlayer?playerSetup.equippedTack:null,
    temperamentTrouble:null,
    gateChecked:false,
    startReaction:"普通",
    temperamentRoll:raceRandom(),
    flowFit: 1,
    trackBias:trackBiasFor(i+1,effectiveStyle),
    stretchRoute: raceRandom() < .58 ? "outside" : "inside",
    routeChosen: false,
    player: isPlayer,
    finished: false,
    finishTime: null,
    wobble: raceRandom() * 10,
  };
}

function buildOpponentAbilities() {
  // プレイヤー能力には追従せず、レース格ごとの固定帯から編成する。
  const standards={新馬:630,未勝利:640,"1勝":700,"2勝":750,"3勝":800,オープン:830,G3:860,G2:900,G1:940};
  const raceStandard=standards[playerSetup.raceClass]??playerSetup.difficulty;
  const offsets = playerSetup.raceClass==="G1"
    ? [-45,-30,-15,0,10,20,30]
    : [-50, -30, -10, 0, 10, 30, 50];
  return offsets
    .map(offset => raceStandard + offset + (raceRandom() < .28 ? (raceRandom() < .5 ? -10 : 10) : 0))
    .sort(() => raceRandom() - .5);
}

function buildOpponentNames(){
  const matching=RIVAL_CATALOG.filter(r=>r.surface===raceSurface&&TOTAL>=r.min-200&&TOTAL<=r.max+200);
  const fallback=RIVAL_CATALOG.filter(r=>r.surface===raceSurface);
  const pool=[...(matching.length>=7?matching:fallback)];
  for(let i=pool.length-1;i>0;i--){const j=Math.floor(raceRandom()*(i+1));[pool[i],pool[j]]=[pool[j],pool[i]]}
  return pool.slice(0,7).map(r=>r.name);
}

function buildOpponentRivals(){
  const shuffle=pool=>{for(let i=pool.length-1;i>0;i--){const j=Math.floor(raceRandom()*(i+1));[pool[i],pool[j]]=[pool[j],pool[i]]}return pool};
  const graded=["G1","G2","G3"].includes(playerSetup.raceClass);
  const legendCount=!graded?0:playerSetup.raceClass==="G1"?2:playerSetup.raceClass==="G2"?(raceRandom()<.5?1:2):1;
  const legendPool=RIVAL_CATALOG.filter(r=>r.surface===raceSurface&&TOTAL>=r.min-150&&TOTAL<=r.max+150).map(r=>({...r,legend:true}));
  const fictionPool=FICTIONAL_RIVALS.filter(r=>r.surface===raceSurface&&TOTAL>=r.min-200&&TOTAL<=r.max+200);
  return [...shuffle(legendPool).slice(0,legendCount),...shuffle([...fictionPool]).slice(0,7-legendCount)];
}

function resetRace() {
  clearTimeout(gateStartTimer);
  cancelAnimationFrame(raf);
  randomState = raceSeed;
  simulationAccumulator = 0;
  const styles = STYLE_PATTERNS[raceSeed % STYLE_PATTERNS.length];
  opponentAbilities = buildOpponentAbilities();
  opponentRivals = buildOpponentRivals();
  opponentNames = opponentRivals.map(r=>r.name);
  playerNumber=1+Math.floor(raceRandom()*8);
  horses = Array.from({ length: 8 }, (_, i) => makeHorse(i, styles));
  visionRanks=new Map(horses.map((h,i)=>[h.id,i+1]));visionRankStamp=0;
  if(elevationHorsesEl)elevationHorsesEl.innerHTML=horses.map(h=>`<i data-elevation-horse="${h.id}" class="${h.player?"player":""}" style="background:${h.color}">${h.id}</i>`).join("");
  if(elevationPathEl){
    const points=Array.from({length:65},(_,i)=>{
      const n=i/64,progress=START_PROGRESS+n*TOTAL/LAP;
      return `${i?"L":"M"}${2+n*316} ${33-courseElevation(progress)}`;
    });
    elevationPathEl.setAttribute("d",points.join(" "));
  }
  fieldAverageAbility = horses.reduce((sum, h) => sum + h.ability, 0) / horses.length;
  racePace = analyzePace(horses);
  assignFlowFit(horses, racePace);
  calculateOdds(horses);
  window.dispatchEvent(new CustomEvent("dotkeiba:preview-ready",{detail:{
    weather:playerSetup.weather,going:playerSetup.going,bias:trackBiasLabel(),
    entries:horses.map(h=>({
      id:h.id,name:h.name,style:h.styleLabel||h.style,odds:h.odds,popularity:h.popularity,player:h.player,
      condition:h.condition>=1.008?"絶好":h.condition>=1.002?"好調":h.condition>=.994?"普通":"下降",
      comment:h.trackBias>1.01?"枠とコース相性が魅力":h.ability>=fieldAverageAbility+25?"地力上位、勝ち負け必至":h.style==="逃げ"&&racePace.escapeCount===1?"単騎なら粘り込み十分":h.style==="追込"&&racePace.escapeCount>=3?"流れ向けば末脚炸裂":"展開ひとつで上位争い"
    }))
  }}));
  state = "ready";
  raceClock = 0;
  preRaceClock = 0;
  weatherClock = 0;
  waitingMotionClock = 0;
  gateDifficultHorseId = null;
  cheerClock = 0;
  split1000Time = null;
  measuredPace = "未確定";
  lastTime = 0;
  commentaryStamp = new Set();
  remainingEl.textContent = `残り ${TOTAL}m`;
  raceTimeEl.textContent = "0:00.0";
  split1000El.textContent = "--:--.-";
  finishTimeEl.textContent = "--:--.-";
  phaseEl.textContent = "発走準備";
  slopeStateEl.textContent = "平坦";
  const slopeMeta=document.querySelector(".slope-status span:last-child");if(slopeMeta)slopeMeta.textContent=`${currentRaceVenue}${raceSurface} 高低差${trackProfile().elevation}m`;
  setCommentary("各馬、ゲートに入りました。",true);
  winnerPopup.classList.remove("show");
  winnerPopup.setAttribute("aria-hidden","true");
  pendingResultDetail=null;
  favoriteRaceButton.disabled=false;
  favoriteRaceButton.textContent="☆ お気に入り保存";
  favoriteRaceButton.hidden=archiveReplay;
  showResultButton.textContent=archiveReplay?"戦歴へ戻る":"結果へ";
  paceDisplayEl.textContent = `展開予測：${racePace.name}（逃げ${racePace.escapeCount}頭）`;
  benchmarkTimesEl.textContent=`基準 ${formatTime(playerSetup.benchmarkTime||playerSetup.baseTime)}　${playerSetup.recordVerified?"公式レコード":"参考最速値"} ${formatTime(playerSetup.recordTime||playerSetup.baseTime*.965)}`;
  if(weatherDisplayEl)weatherDisplayEl.textContent=`${playerSetup.raceMonth||""}月　天気 ${playerSetup.weather}　${raceSurface} ${playerSetup.going}　傾向 ${trackBiasLabel()}`;
  startButton.textContent = "レース開始";
  startButton.disabled = false;
  pauseButton.disabled = true;
  gateSkipButton.hidden = true;
  raceTestBackButton.hidden = !courseAuditMode;
  speedButton.hidden = true;
  pauseButton.textContent = "一時停止";
  multiplier = 1;
  speedButton.textContent = "レース速度：通常";
  draw();
  renderRanking();
}

function assignFlowFit(entries, pace) {
  entries.forEach(h => {
    let fit = 1;
    if (pace.escapeCount >= 3) {
      fit = h.style === "追込" ? 1.045 : h.style === "差し" ? 1.032 : h.style === "逃げ" ? .955 : .982;
    } else if (pace.escapeCount === 2) {
      fit = h.style === "差し" ? 1.022 : h.style === "追込" ? 1.015 : h.style === "逃げ" ? .985 : 1;
    } else if (pace.escapeCount === 1) {
      fit = h.style === "逃げ" ? 1.035 : h.style === "先行" ? 1.018 : h.style === "追込" ? .965 : .985;
    } else {
      fit = h.style === "先行" ? 1.025 : h.style === "差し" ? .975 : h.style === "追込" ? .95 : 1;
    }
    // 馬群や仕掛けのタイミングによる小さな揺らぎ。
    h.flowFit = fit + (raceRandom() - .5) * .018;
  });
}

function calculateOdds(entries) {
  // オッズは基礎能力のみから算出。脚質、展開、当日の調子は含めない。
  // 同レベル中心のメンバー構成として、極端な万馬券表示にならないようにする。
  const strongest = Math.max(...entries.map(h => h.ability));
  const weights = entries.map(h => Math.exp((h.ability - strongest) / 52));
  const totalWeight = weights.reduce((sum, value) => sum + value, 0);
  const marketProbabilities = weights.map(weight => (weight / totalWeight) * .78);
  const ranked = entries
    .map((h, i) => ({ h, probability: marketProbabilities[i] }))
    .sort((a, b) => b.probability - a.probability);
  ranked.forEach((entry, index) => {
    entry.h.popularity = index + 1;
    entry.h.odds = Math.min(99.9, Math.max(1.4, Math.round((1 / entry.probability) * 10) / 10));
  });
}

function analyzePace(entries) {
  const escapeCount = entries.filter(h => h.style === "逃げ").length;
  const splitNoise = (raceRandom() - .5) * 500;
  const finishNoise = (raceRandom() - .5) * 1800;
  const distanceBase = playerSetup.baseTime || TOTAL * 62;
  const baseSplit = distanceBase * 1000 / TOTAL;
  const ageTwo=playerSetup.age===2;
  const minSplit=TOTAL<=1000
    ? (["G1","G2","G3","オープン"].includes(playerSetup.raceClass)?54500:55500)
    : raceSurface==="芝"?(ageTwo?59500:58500):(ageTwo?61500:60200);
  const maxSplit=TOTAL<=1000?60500:raceSurface==="芝"?64500:66500;
  const boundedSplit=value=>Math.max(minSplit,Math.min(maxSplit,value));
  if (escapeCount >= 3) {
    return {
      name: "ハイペース",
      escapeCount,
      targetSplit: boundedSplit(baseSplit - 900 + splitNoise),
      targetFinish: distanceBase - 300 + finishNoise,
    };
  }
  if (escapeCount === 2) {
    return {
      name: "ややハイ",
      escapeCount,
      targetSplit: boundedSplit(baseSplit - 400 + splitNoise),
      targetFinish: distanceBase + finishNoise,
    };
  }
  if (escapeCount === 1) {
    return {
      name: "スローペース",
      escapeCount,
      targetSplit: boundedSplit(baseSplit + 500 + splitNoise),
      targetFinish: distanceBase + 600 + finishNoise,
    };
  }
  return {
    name: "超スロー",
    escapeCount,
    targetSplit: boundedSplit(baseSplit + 1300 + splitNoise),
    targetFinish: distanceBase + 1400 + finishNoise,
  };
}

function raceDistance(h) {
  return Math.max(0, (h.progress - START_PROGRESS) * LAP);
}

function order() {
  return [...horses].sort((a,b)=>{
    if(a.finished&&b.finished)return a.finishTime-b.finishTime;
    if(a.finished)return-1;
    if(b.finished)return 1;
    return b.progress-a.progress;
  });
}

function update(dt, clockDt) {
  raceClock += clockDt;
  const leaders = order();
  const leader = leaders[0];
  const leaderDistance = Math.min(TOTAL, raceDistance(leader));
  const rawRemaining=TOTAL-leaderDistance;
  const remaining = leader.finished||rawRemaining<2 ? 0 : Math.max(0,Math.ceil(rawRemaining));
  const expectedDistance = raceClock <= racePace.targetSplit
    ? 1000 * raceClock / racePace.targetSplit
    : 1000 + Math.max(0,TOTAL-1000) * (raceClock - racePace.targetSplit) /
      Math.max(1, racePace.targetFinish - racePace.targetSplit);
  // 想定ラップから大きく外れないよう、先頭の速度を緩やかに補正する。
  // 脚質は着順と位置取りへ効かせ、時計だけが毎回暴走するのを防ぐ。
  const paceError = expectedDistance - leaderDistance;
  const paceControl = Math.max(.48, Math.min(1.12, 1 + paceError / 105));
  if (split1000Time === null && leaderDistance >= 1000) {
    split1000Time = raceClock;
    measuredPace = classify1000mPace(split1000Time);
    split1000El.textContent = formatTime(split1000Time);
    paceDisplayEl.textContent = `実測：${measuredPace}（1000m ${formatTime(split1000Time)}）`;
    setCommentary(`${TOTAL===1000?"1000m走破":"1000m通過"} ${formatTime(split1000Time)}、${measuredPace}！`);
  }

  horses.forEach((h) => {
    // ゴール済みの馬もその場で止めず、そのまま減速しながら駆け抜ける。
    if (h.finished) {
      if(h.progress<FINISH_PROGRESS+.075)h.progress+=BASE_PROGRESS_PER_MS*dt*.72;
      return;
    }
    const d = raceDistance(h);
    const normalized = d / TOTAL;
    const paceDrain = racePace.name === "ハイペース" ? .10 : racePace.name === "ややハイ" ? .05 : -.025;
    const styleDrain =
      h.style === "逃げ" && racePace.escapeCount >= 2 ? .09 :
      h.style === "追込" ? -.025 : 0;
    let temperamentDrain=0;
    if(!h.gateChecked&&normalized<.035){
      h.gateChecked=true;
      const lowDash=Math.max(0,(560-h.dash)/560);
      const lowGate=Math.max(0,(620-h.gateSkill)/620);
      const timidness=Math.max(0,(45-h.temperamentValue)/45);
      const hoodReduction=h.equippedTack==="hood"?.42:1;
      const lateBreakRisk=Math.min(.14,(.012+lowDash*.045+lowGate*.065+timidness*.035)*hoodReduction);
      if(raceRandom()<lateBreakRisk)h.temperamentTrouble="出遅れ";
    }
    const temperamentRisk=h.temperamentValue>=60
      ? .035+(h.temperamentValue-60)*.004
      : h.temperamentValue<=40?.035+(40-h.temperamentValue)*.004:.018;
    if(normalized<.42&&h.temperamentRoll<temperamentRisk){
      const blinkers=h.equippedTack==="blinkers";
      const hood=h.equippedTack==="hood";
      const cheek=h.equippedTack==="cheekpieces";
      if(h.temperamentValue>=60){
        h.temperamentTrouble="掛かり";
        temperamentDrain=blinkers?.15:.13;
      }else if(h.temperamentValue<=40){
        if(!cheek&&h.temperamentTrouble!=="出遅れ")h.temperamentTrouble="物見";
      }
    }
    const currentGradient = courseGradient(h.progress);
    const slopeDrain = currentGradient.type === "up" ? .045 * currentGradient.strength : 0;
    let measuredDrain = 0;
    if (split1000Time !== null) {
      const splitSeconds = split1000Time / 1000;
      if (splitSeconds < 58.5) {
        measuredDrain = h.style === "逃げ" ? .28 : h.style === "先行" ? .16 : .03;
      } else if (splitSeconds < 60) {
        measuredDrain = h.style === "逃げ" ? .16 : h.style === "先行" ? .09 : .015;
      }
    }
    h.stamina = Math.max(.02, 1 - normalized *
      (.74 + h.id * .004 + paceDrain + styleDrain + measuredDrain + slopeDrain + temperamentDrain));

    let styleFactor = 1;
    if (h.style === "逃げ") {
      styleFactor = normalized < .72 ? 1.04 : .965;
      // 単騎逃げなら楽に運べて直線でも粘る。逃げ争いでは終盤に消耗。
      if (racePace.escapeCount === 1) {
        styleFactor *= normalized < .78 ? 1.014 : 1.045;
      } else if (racePace.escapeCount >= 3 && normalized > .68) {
        styleFactor *= .92;
      } else if (racePace.escapeCount === 2 && normalized > .76) {
        styleFactor *= .96;
      }
    }
    if (h.style === "先行") {
      styleFactor = normalized < .75 ? 1.014 : 1.0;
      if (racePace.escapeCount >= 3 && normalized > .72) styleFactor *= .975;
      if (racePace.escapeCount === 1 && normalized > .76) styleFactor *= 1.018;
    }
    if (h.style === "差し") {
      styleFactor = normalized < .62 ? .982 : 1.045;
      if (racePace.escapeCount >= 3 && normalized > .68) styleFactor *= 1.06;
      if (racePace.escapeCount === 1 && normalized > .72) styleFactor *= .965;
    }
    if (h.style === "追込") {
      styleFactor = normalized < .72 ? .965 : 1.078;
      if (racePace.escapeCount >= 3 && normalized > .72) styleFactor *= 1.075;
      if (racePace.escapeCount === 1 && normalized > .72) styleFactor *= .94;
    }
    // 名馬ごとの走り方。大逃げは前半を引き離し、まくりは向正面から進出する。
    if(h.styleLabel==="大逃げ")styleFactor*=normalized<.58?1.032:normalized>.78?.955:1;
    if(h.styleLabel==="まくり")styleFactor*=normalized<.42?.975:normalized<.78?1.052:1.015;
    if(h.rivalTrait==="kick"&&normalized>.76)styleFactor*=1.018;
    if(h.rivalTrait==="stamina"&&TOTAL>=2400&&normalized>.62)styleFactor*=1.014;
    if(h.rivalTrait==="steady")styleFactor*=.997+h.stamina*.006;
    if(h.rivalTrait==="guts"&&normalized>.88)styleFactor*=1.014;

    // 1000mの実測時計を後半の消耗へ反映する。
    // 57秒台のような暴走ペースでは、逃げ・先行馬は直線で強く失速する。
    if (split1000Time !== null && normalized > .43) {
      const splitSeconds = split1000Time / 1000;
      const lateStage = Math.min(1, Math.max(0, (normalized - .43) / .57));
      if (splitSeconds < 58.5) {
        if (h.style === "逃げ") styleFactor *= 1 - .25 * lateStage;
        if (h.style === "先行") styleFactor *= 1 - .14 * lateStage;
        if (h.style === "差し") styleFactor *= 1 + .09 * lateStage;
        if (h.style === "追込") styleFactor *= 1 + .13 * lateStage;
      } else if (splitSeconds < 60) {
        if (h.style === "逃げ") styleFactor *= 1 - .14 * lateStage;
        if (h.style === "先行") styleFactor *= 1 - .07 * lateStage;
        if (h.style === "差し") styleFactor *= 1 + .05 * lateStage;
        if (h.style === "追込") styleFactor *= 1 + .08 * lateStage;
      } else if (splitSeconds > 62) {
        if (h.style === "逃げ") styleFactor *= 1 + .055 * lateStage;
        if (h.style === "先行") styleFactor *= 1 + .025 * lateStage;
        if (h.style === "追込") styleFactor *= 1 - .055 * lateStage;
      }
    }

    const curve = coursePoint(h.progress, h.lane);
    const curvePenalty = curve.curve ? .974 + h.lane * .003 : 1;
    const gradient = courseGradient(h.progress);
    const slopePenalty =
      gradient.type === "up"
        ? 1 - gradient.strength * (.025 + (1 - h.stamina) * .026)
        : gradient.type === "down"
          ? 1 + gradient.strength * .009
          : 1;
    const kick = normalized > .78 ? .97 + h.stamina * .09 : 1;
    const noise = 1 + Math.sin(raceClock * .003 + h.wobble) * .008;
    // 時計の基準は維持しつつ、このレース内での相対能力差を着順へ反映する。
    const abilityFactor = 1 + (h.ability - fieldAverageAbility) * .00045;
    // 絶対能力980以上だけを歴代級として扱う。
    // クラス基準に連動させると、通常の重賞馬までレコード補正を受けてしまう。
    const eliteThreshold=980;
    const elitePoints=Math.max(0,h.ability-eliteThreshold);
    const eliteFactor=1+elitePoints*.000165+Math.max(0,h.ability-970)*.000125;
    const goingSeverity={"良":0,"稍重":1,"重":2,"不良":3}[playerSetup.going]??0;
    const goingBase=raceSurface==="芝"
      ? [1,.993,.978,.958][goingSeverity]
      : [1,.998,1.002,.992][goingSeverity];
    const goingTalent=(h.heavyTrack-550)/10000*goingSeverity;
    const goingFactor=Math.max(.94,goingBase+goingTalent);
    // ダッシュ力はスタートから序盤約400mまでの加速と位置取りに反映する。
    // 高いほど前へ行きやすいが、終盤の走力そのものは直接強化しない。
    const dashStage = Math.max(0, 1 - normalized / Math.min(.30, 400 / TOTAL));
    const dashFactor = 1 + (h.dash - 540) * .00018 * dashStage;
    const startFactor=h.startReaction==="好スタート"&&normalized<.08?1.014:1;
    const temperamentFactor=
      h.temperamentTrouble==="出遅れ"&&normalized<.22?.955:
      h.temperamentTrouble==="物見"&&normalized>.25&&normalized<.72?.978:
      h.temperamentTrouble==="掛かり"&&normalized<.45?1.018:1;
    const tackFactor=h.equippedTack==="blinkers"
      ? (normalized<.55?1.006:1)
      : h.equippedTack==="cheekpieces"&&normalized>.55?1.006:1;
    // 低確率の当日不利。能力上位馬も展開や進路次第では負ける。
    const troubleFactor =
      h.trouble < .055 && normalized > .62 && normalized < .88 ? .965 :
      h.trouble > .965 && normalized > .72 ? 1.018 : 1;
    // 展開補正は中盤から徐々に効かせる。能力差を消し切らず、
    // 数ポイント程度の差なら脚質とペース次第で逆転できる強さにする。
    const flowStage = Math.max(0, Math.min(1, (normalized - .38) / .42));
    const flowFactor = 1 + (h.flowFit - 1) * flowStage;
    const localVenues=["門別","盛岡","浦和","船橋","大井","川崎","金沢","名古屋","園田","高知","佐賀"];
    const traitFactor=
      h.rivalTrait==="tokyo"&&currentRaceVenue==="東京"?1.015:
      h.rivalTrait==="straight"&&currentRaceVenue==="新潟"&&TOTAL===1000?1.022:
      h.rivalTrait==="local"&&localVenues.includes(currentRaceVenue)?1.014:
      h.rivalTrait==="power"&&(gradient.type==="up"||raceSurface==="ダート")?1.009:
      h.rivalTrait==="pace"&&["ハイペース","ややハイ"].includes(racePace.name)?1.012:1;
    let velocity = BASE_PROGRESS_PER_MS * paceControl * abilityFactor * eliteFactor * goingFactor * h.condition * h.trackBias *
      styleFactor * dashFactor * startFactor * temperamentFactor * tackFactor * curvePenalty * slopePenalty * kick * noise * troubleFactor * flowFactor * traitFactor;

    // 3～4コーナーまでは全馬が内寄り。差し・追込は勝負所で外へ出すか、
    // 内を突いて直線勝負を選ぶ。逃げ馬は最内を維持する。
    if(normalized>.67&&!h.routeChosen){
      h.routeChosen=true;
      if(h.style==="逃げ")h.targetLane=7.3;
      else if(h.style==="先行")h.targetLane=6.65-(h.id%2)*.3;
      else if(h.stretchRoute==="outside")h.targetLane=h.style==="追込"?3.2:4.0;
      else h.targetLane=6.75-(h.id%2)*.32;
    }
    if(normalized>.90&&h.stretchRoute==="outside")h.targetLane=Math.min(5.0,h.targetLane+.45);

    const blockers = horses.filter(o =>
      o !== h && !o.finished &&
      o.progress > h.progress && o.progress - h.progress < .012 &&
      Math.abs(o.lane - h.lane) < .62
    );
    if (blockers.length) {
      velocity *= .82;
      if (raceRandom() < dt * .0012) {
        const options = [h.lane - .8, h.lane + .65].filter(l => l >= 2.4 && l <= 7.4);
        h.targetLane = options.sort((a, b) => laneCongestion(a, h) - laneCongestion(b, h))[0];
      }
    } else if (normalized>.65&&raceRandom() < dt * .00008) {
      h.targetLane = Math.max(2.4, Math.min(7.4, h.targetLane + (raceRandom() < .5 ? -.35 : .35)));
    }

    h.lane += (h.targetLane - h.lane) * Math.min(1, dt * .0017);
    h.progress += velocity * dt;

    if (h.progress >= FINISH_PROGRESS) {
      // 展開の上振れだけで標準馬がレコードを更新しないようにする。
      // 能力950未満には公式レコード直前に小さな時計の壁を設ける。
      const recordBarrier=Number.isFinite(playerSetup.recordTime)&&h.ability<980
        ? playerSetup.recordTime+80+(980-h.ability)*6
        : 0;
      if(recordBarrier&&raceClock<recordBarrier){
        h.progress=FINISH_PROGRESS-.00008;
        return;
      }
      // 着順判定はゴール到達時に確定するが、描画位置は止めない。
      h.progress = FINISH_PROGRESS + BASE_PROGRESS_PER_MS*dt*.35;
      h.finished = true;
      h.finishTime = raceClock;
    }
  });

  remainingEl.textContent = `残り ${remaining}m`;
  raceTimeEl.textContent = formatTime(raceClock);
  if(elevationHorsesEl)horses.forEach(h=>{
    const dot=elevationHorsesEl.querySelector(`[data-elevation-horse="${h.id}"]`);if(!dot)return;
    const normalized=Math.max(0,Math.min(1,raceDistance(h)/TOTAL));
    dot.style.left=`${1+normalized*98}%`;dot.style.bottom=`${5+courseElevation(h.progress)}px`;
  });
  const homeStraight=Math.round(trackProfile().straight);
  phaseEl.textContent =
    remaining === 0 ? "確定" :
    remaining <= homeStraight ? "最後の直線" :
    remaining <= homeStraight+330 ? "4コーナー" :
    remaining <= homeStraight+760 ? "向正面" : "レース中";
  const leaderGradient = courseGradient(leader.progress);
  slopeStateEl.textContent =
    leaderGradient.type === "up" ? `上り坂 ▲${leaderGradient.label}` :
    leaderGradient.type === "down" ? `下り坂 ▼${leaderGradient.label}` :
    "平坦";

  updateCommentary(remaining);
  if (horses.every(h => h.finished)) finishRace();
}

function updateRunout(dt) {
  horses.forEach(h => {
    if(h.progress<FINISH_PROGRESS+.075)h.progress+=BASE_PROGRESS_PER_MS*dt*.72;
  });
}

function laneCongestion(lane, self) {
  return horses.filter(h =>
    h !== self && Math.abs(h.progress - self.progress) < .025 && Math.abs(h.lane - lane) < .7
  ).length;
}

function updateCommentary(remaining) {
  const currentOrder = order();
  const leader = currentOrder[0];
  const second = currentOrder[1];
  const playerHorse = currentOrder.find(h=>h.player);
  const playerPosition = currentOrder.findIndex(h => h.player) + 1;
  const playerCall = `${playerHorse.id}番${playerHorse.name}`;
  const marks = [
    [TOTAL-120, horses.find(h=>h.player)?.temperamentTrouble==="出遅れ"
      ? `${horses.find(h=>h.player).id}番${horses.find(h=>h.player).name}は出遅れ！ 後方からの競馬になります。`
      : `スタート直後、${leader.id}番${leader.name}が前へ。${second.id}番${second.name}も続きます。`],
    [TOTAL-300, racePace.escapeCount >= 2
      ? `逃げ争い！ ${racePace.escapeCount}頭が先手を主張、ペースが上がる！`
      : `${leader.name}が単騎で先頭へ。落ち着いた流れです。`],
    [TOTAL-500, `序盤の隊列が決まりました。先頭${leader.name}、${playerCall}は${playerPosition}番手。`],
    [Math.max(100, TOTAL-800), `コーナーへ。${leader.name}が先頭、${second.name}が差を詰めます。`],
    [Math.max(100, TOTAL-1100), `中盤です。${playerCall}は現在${playerPosition}番手、まだ脚をためています。`],
    [Math.max(100, TOTAL-1400), `向正面、後方の馬も進出開始。先頭は${leader.name}。`],
    [900, `残り900m、各馬が仕掛けのタイミングをうかがいます。`],
    [700, `3コーナーから4コーナー！ ${second.name}が先頭へ迫る！`],
    [525, racePace.escapeCount >= 3
      ? `最後の直線！ 前が苦しい、外から差し・追込勢！`
      : `最後の直線！ 逃げ馬がまだ粘る、後続は届くか！`],
    [400, `残り400！ 先頭${leader.name}、${playerCall}は${playerPosition}番手から追います！`],
    [250, `残り250！ 横に広がって追い比べ！`],
    [150, `${leader.name}が先頭！ ${second.name}も並びかける！`],
    [80, `ゴール前！ 抜け出すのは${leader.id}番${leader.name}！`],
  ];
  const hit = marks.find(([m]) => remaining <= m && !commentaryStamp.has(m));
  if (hit) {
    commentaryStamp.add(hit[0]);
    setCommentary(hit[1]);
  }
}

function finishRace() {
  if(state==="runout"||state==="finished")return;
  state = "runout";
  startButton.disabled = true;
  pauseButton.disabled = true;
  speedButton.hidden = true;
  const winner = order()[0];
  const isRecord=Number.isFinite(playerSetup.recordTime)&&winner.finishTime<playerSetup.recordTime;
  finishTimeEl.textContent = formatTime(winner.finishTime);
  setCommentary(isRecord
    ? `レコード更新！ ${formatTime(winner.finishTime)}！ 1着は${winner.id}番 ${winner.name}！`
    : `ゴール！ 各馬そのままゴール板を駆け抜けます。1着は${winner.id}番 ${winner.name}！`);
  renderRanking();
  setTimeout(()=>{
    state="finished";
    document.querySelector("#winnerSaddle").textContent=winner.id;
    document.querySelector("#winnerSaddle").style.background=winner.color;
    document.querySelector("#winnerSaddle").style.color=numberTextColor(winner.id);
    document.querySelector("#winnerNumber").textContent=`${winner.id}番`;
    document.querySelector("#winnerNumber").style.color=winner.color;
    document.querySelector("#winnerName").textContent=winner.name;
    document.querySelector("#winnerTime").textContent=`${formatTime(winner.finishTime)}${isRecord?" NEW RECORD":""}`;
    winnerPopup.classList.add("show");
    winnerPopup.setAttribute("aria-hidden","false");
    pendingResultDetail={
      winnerTime:formatTime(winner.finishTime),isRecord,
      raceSeed,setup:{...playerSetup},measuredPace,
      order:order().map(h=>({
        id:h.id,name:h.name,color:h.color,odds:h.odds,style:h.style,
        finishTime:formatTime(h.finishTime),finishMs:h.finishTime,player:h.player,
        isRecord:Number.isFinite(playerSetup.recordTime)&&h.finishTime<playerSetup.recordTime,
        temperamentTrouble:h.temperamentTrouble,
      }))
    };
  },1300);
}

function classify1000mPace(milliseconds) {
  const seconds = milliseconds / 1000;
  if (seconds < 58.5) return "超ハイペース";
  if (seconds < 60) return "ハイペース";
  if (seconds < 61.5) return "平均ペース";
  if (seconds < 63) return "スローペース";
  return "超スローペース";
}

function formatTime(milliseconds) {
  const totalTenths = Math.floor(milliseconds / 100);
  const minutes = Math.floor(totalTenths / 600);
  const seconds = Math.floor((totalTenths % 600) / 10);
  const tenths = totalTenths % 10;
  return `${minutes}:${String(seconds).padStart(2, "0")}.${tenths}`;
}

function numberTextColor(id) {
  return id === 1 || id === 5 ? "#111" : "#fff";
}

function coursePoint(progress,lane=3){
  return baseCoursePoint(progress,lane);
}

function baseCoursePoint(progress, lane = 3) {
  if(currentCourseSpec.route==="直線"){
    const ratio=Math.max(0,Math.min(1,(progress-START_PROGRESS)/(TOTAL/LAP)));
    return horizontalLayout
      ? {x:24+ratio*312,y:102+lane*5,angle:0,curve:false}
      : layoutV2
        ? {x:18+ratio*324,y:88+lane*10,angle:0,curve:false}
        : {x:36+ratio*288,y:145+lane*12,angle:0,curve:false};
  }
  let p = ((progress % 1) + 1) % 1;
  const rightTurn=trackProfile().turn==="右";
  // 元の中心線は時計回り。検証画面の左回りは決勝線を軸に座標順だけを反転する。
  // 単純な 1-p ではゴール位置まで移動するため、2*FINISH_PROGRESS-p で位置を固定する。
  const reverseTraversal=!rightTurn;
  if(reverseTraversal)p=((2*FINISH_PROGRESS-p)%1+1)%1;
  if(horizontalLayout){
    const inset=lane*4,left=43+inset,right=317-inset,top=50+lane*3,bottom=230-lane*3;
    const cy=(top+bottom)/2,rx=Math.max(28,48-inset*.12),straight=.39,curve=.11;
    if(p<straight){const t=p/straight;return{x:left+(right-left)*t,y:top,angle:0,curve:false}}
    if(p<straight+curve){const t=(p-straight)/curve,a=-Math.PI/2+t*Math.PI;return{x:right+Math.cos(a)*rx,y:cy+Math.sin(a)*(bottom-top)/2,angle:a+Math.PI/2,curve:true}}
    if(p<straight*2+curve){const t=(p-straight-curve)/straight;return{x:right-(right-left)*t,y:bottom,angle:Math.PI,curve:false}}
    const t=(p-straight*2-curve)/curve,a=Math.PI/2+t*Math.PI;
    return{x:left+Math.cos(a)*rx,y:cy+Math.sin(a)*(bottom-top)/2,angle:a+Math.PI/2,curve:true};
  }
  const officialPath=window.COURSE_LAYOUTS?.[currentRaceVenue]?.layouts?.[currentCourseSpec.layoutKey];
  if(layoutV2&&officialPath?.length>2){
    const pt=officialCoursePoint(officialPath,p,lane);
    if(reverseTraversal)pt.angle+=Math.PI;
    pt.x=360-pt.x;pt.y=270-pt.y+COURSE_Y_SHIFT;pt.angle+=Math.PI;
    return pt;
  }
  const pt=verticalCoursePoint(p,lane);
  // 座標だけでなく馬体の向きも実際の右回り進行方向へ反転する。
  if(reverseTraversal)pt.angle+=Math.PI;
  if(!layoutV2)return pt;
  // レイアウトV2：縦画面のまま、実測ベースの縦型コース形状を90度回転して
  // 画面上部の横長コースへ写像する。ホーム直線（縦型では右端）が上辺＝スタンド側。
  return{
    x:-0.7+pt.y*.723,
    y:50+(332-pt.x)*.632,
    angle:Math.atan2(-.632*Math.cos(pt.angle),.723*Math.sin(pt.angle)),
    curve:pt.curve,
  };
}

function cleanOfficialGeometry(path){
  if(COURSE_PATH_CACHE.has(path))return COURSE_PATH_CACHE.get(path);
  const points=path.map(([x,y])=>[180+(x-180)*.92,145+(y-145)*.72]);
  const xs=points.map(q=>q[0]),ys=points.map(q=>q[1]);
  const left=Math.max(14,Math.min(...xs)),right=Math.min(346,Math.max(...xs));
  const top=Math.max(76,Math.min(...ys)),bottom=Math.min(224,Math.max(...ys));
  const clamp=(v,min,max)=>Math.max(min,Math.min(max,v));
  const leftRadius=clamp((points[0]?.[0]??left+42)-left,36,58);
  const rightRadius=clamp(right-(points[2]?.[0]??right-42),36,58);
  const geometry={left,right,top,bottom,leftRadius,rightRadius};
  COURSE_PATH_CACHE.set(path,geometry);return geometry;
}

function officialCoursePoint(rawPath,p,lane){
  const g=cleanOfficialGeometry(rawPath),straightShare=trackProfile().straightShare,curveShare=(1-straightShare*2)/2;
  const bezier=(a,b,c,d,t)=>{const u=1-t;return u*u*u*a+3*u*u*t*b+3*u*t*t*c+t*t*t*d};
  const derivative=(a,b,c,d,t)=>3*(1-t)*(1-t)*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c);
  let x,y,dx,dy,curve=false;
  const topLeft=g.left+g.leftRadius,topRight=g.right-g.rightRadius,bottomRight=g.right-g.rightRadius*.92,bottomLeft=g.left+g.leftRadius*.92;
  if(p<straightShare){const t=p/straightShare;x=topLeft+(topRight-topLeft)*t;y=g.top;dx=1;dy=0}
  else if(p<straightShare+curveShare){
    const t=(p-straightShare)/curveShare;x=bezier(topRight,g.right,g.right,bottomRight,t);y=bezier(g.top,g.top,g.bottom,g.bottom,t);dx=derivative(topRight,g.right,g.right,bottomRight,t);dy=derivative(g.top,g.top,g.bottom,g.bottom,t);curve=true;
  }else if(p<straightShare*2+curveShare){const t=(p-straightShare-curveShare)/straightShare;x=bottomRight+(bottomLeft-bottomRight)*t;y=g.bottom;dx=-1;dy=0}
  else{
    const t=(p-straightShare*2-curveShare)/curveShare;x=bezier(bottomLeft,g.left,g.left,topLeft,t);y=bezier(g.bottom,g.bottom,g.top,g.top,t);dx=derivative(bottomLeft,g.left,g.left,topLeft,t);dy=derivative(g.bottom,g.bottom,g.top,g.top,t);curve=true;
  }
  const angle=Math.atan2(dy,dx);
  const offset=(lane-4.2)*2.35;
  return{x:x-Math.sin(angle)*offset,y:y+Math.cos(angle)*offset,angle,curve};
}

function verticalCoursePoint(p,lane){
  // 東京競馬場の航空形状を90度回転。右が525.9mのホーム直線、
  // 左が向正面、上下は緩い大コーナーとして描く。
  const profile=trackProfile(),straightShare=profile.straightShare,curveShare=(1-straightShare*2)/2;
  const inset=lane*5.1,left=28+inset,right=332-inset,top=78+inset,bottom=422-inset;
  const cx=180,rx=(right-left)/2,ry=(58*profile.roundness)-inset*.18;
  if(p<straightShare){
    const t=p/straightShare;
    return {x:right,y:top+(bottom-top)*t,angle:Math.PI/2,curve:false};
  }
  if(p<straightShare+curveShare){
    const t=(p-straightShare)/curveShare,a=t*Math.PI;
    return {x:cx+Math.cos(a)*rx,y:bottom+Math.sin(a)*ry,angle:a+Math.PI/2,curve:true};
  }
  if(p<straightShare*2+curveShare){
    const t=(p-straightShare-curveShare)/straightShare;
    return {x:left,y:bottom-(bottom-top)*t,angle:-Math.PI/2,curve:false};
  }
  const t=(p-straightShare*2-curveShare)/curveShare,a=Math.PI+t*Math.PI;
  return {x:cx+Math.cos(a)*rx,y:top+Math.sin(a)*ry,angle:a+Math.PI/2,curve:true};
}

function courseElevation(progress){
  const p=((progress%1)+1)%1;
  const points=[[0,16],[.05,16],[.29,8],[.34,8],[.43,14],[.66,10],[.76,22],[1,16]];
  for(let i=1;i<points.length;i++)if(p<=points[i][0]){
    const [x1,y1]=points[i-1],[x2,y2]=points[i],t=(p-x1)/(x2-x1||1);return y1+(y2-y1)*t;
  }
  return 16;
}
function courseGradient(progress) {
  const p = ((progress % 1) + 1) % 1;
  if(p>.05&&p<.29)return {type:"down",strength:.8,label:"長い下り"};
  if(p>.34&&p<.43)return {type:"up",strength:.75,label:"3角手前の上り"};
  if(p>.43&&p<.66)return {type:"down",strength:.35,label:"緩い下り"};
  if(p>.66&&p<.76)return {type:"up",strength:1,label:"直線の坂"};
  return {type:"flat",strength:0,label:"平坦"};
}

function drawPixelHorse(h, pos) {
  const scale = 2;
  const c = Math.cos(pos.angle), s = Math.sin(pos.angle);
  const local = (x, y) => ({
    x: Math.round(pos.x + (x * c - y * s) * scale),
    y: Math.round(pos.y + (x * s + y * c) * scale),
  });
  const block = (x, y, color, w = 1, hh = 1) => {
    const p = local(x, y);
    ctx.fillStyle = color;
    ctx.fillRect(p.x, p.y, Math.max(2, w * scale), Math.max(2, hh * scale));
  };
  block(-2, 0, "#492812", 4, 2);
  block(2, -1, "#7b461f", 2, 2);
  block(-1, -2, h.color, 2, 1);
  block(0, -3, h.color);
  block(-2, 2, "#17120e");
  block(1, 2, "#17120e");

  ctx.fillStyle = h.color;
  ctx.fillRect(Math.round(pos.x - 4), Math.round(pos.y - 13), 9, 9);
  ctx.strokeStyle = h.id === 1 ? "#333" : "#f4d76a";
  ctx.lineWidth = 1;
  ctx.strokeRect(Math.round(pos.x - 4), Math.round(pos.y - 13), 9, 9);
  ctx.fillStyle = numberTextColor(h.id);
  ctx.font = "bold 8px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(h.id, Math.round(pos.x), Math.round(pos.y - 6));
  if(h.equippedTack){
    const tack=local(5,-2);
    ctx.fillStyle=h.equippedTack==="hood"?"#5aa8df":h.equippedTack==="blinkers"?"#e94e45":"#f0c84b";
    ctx.fillRect(tack.x-2,tack.y-2,4,4);
  }
  if(h.player){
    const marker=local(0,-12);
    ctx.fillStyle="#ffe45c";
    ctx.beginPath();ctx.moveTo(marker.x,marker.y+5);ctx.lineTo(marker.x-5,marker.y-2);ctx.lineTo(marker.x+5,marker.y-2);ctx.closePath();ctx.fill();
  }
}

function drawVisionCandidateHorse(x,y,h,scale=.62){
  ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);
  const coat=h.player?"#d08a42":"#a9612f";
  ctx.fillStyle=coat;ctx.strokeStyle="#3c2418";ctx.lineWidth=2;
  ctx.fillRect(-22,-6,34,16);ctx.strokeRect(-22,-6,34,16);
  ctx.fillRect(8,-17,10,24);ctx.strokeRect(8,-17,10,24);
  ctx.fillRect(15,-23,18,13);ctx.strokeRect(15,-23,18,13);
  ctx.fillRect(-28,-5,8,5);ctx.fillRect(-16,9,5,15);ctx.fillRect(5,9,5,15);
  ctx.fillStyle=h.color;ctx.fillRect(-12,-4,14,9);
  ctx.fillStyle=numberTextColor(h.id);ctx.font="bold 8px sans-serif";ctx.textAlign="center";ctx.fillText(h.id,-5,4);
  ctx.restore();
}

function drawVisionGoalBoard(x,y){
  ctx.fillStyle="#f7f3df";ctx.fillRect(x,y,4,48);
  ctx.fillStyle="#d73932";ctx.fillRect(x-3,y,10,5);
  ctx.fillStyle="#fff";ctx.fillRect(x-14,y+5,32,14);
  ctx.strokeStyle="#27231e";ctx.lineWidth=2;ctx.strokeRect(x-14,y+5,32,14);
  ctx.fillStyle="#d73932";ctx.font="bold 7px sans-serif";ctx.textAlign="center";ctx.fillText("GOAL",x+2,y+15);
  for(let row=0;row<3;row++)for(let col=0;col<2;col++){
    ctx.fillStyle=(row+col)%2?"#111":"#fff";ctx.fillRect(x-2+col*4,y+21+row*4,4,4);
  }
}

function waitingHorsePosition(h,vx,camY,vw=224,camH=55){
  const slot=h.id-1;
  return {
    x:vx+Math.max(42,vw*.48)+(slot%4)*Math.max(15,vw*.105)+Math.sin(waitingMotionClock*.00075+slot*1.7)*5,
    y:camY+Math.max(15,camH*.33)+Math.floor(slot/4)*Math.max(12,camH*.28)+Math.sin(waitingMotionClock*.00055+slot)*2
  };
}

function drawVisionGate(vx,camY,vw,camH){
  const gateW=Math.max(27,Math.min(34,vw*.17)),gateH=Math.max(31,Math.min(41,camH-7));
  const gateX=vx+vw-gateW-9,gateY=camY+4;
  ctx.fillStyle="#f5f5ed";ctx.fillRect(gateX,gateY,gateW,gateH);
  ctx.strokeStyle="#7f918f";ctx.lineWidth=3;ctx.strokeRect(gateX,gateY,gateW,gateH);
  ctx.fillStyle="#d4ddd8";ctx.fillRect(gateX+7,gateY+5,5,gateH-10);
  const entryOrder=[1,3,5,7,2,4,6,8],step=1000;
  const sequenceIndex=Math.min(7,Math.floor(preRaceClock/step));
  const focus=horses.find(h=>h.id===entryOrder[sequenceIndex]);
  const enteredIds=new Set(entryOrder.slice(0,sequenceIndex));
  horses.filter(h=>h.id!==focus?.id&&!enteredIds.has(h.id)).forEach(h=>{
    const wait=waitingHorsePosition(h,vx,camY,vw,camH);
    drawVisionCandidateHorse(wait.x,wait.y,h,.34);
  });
  const local=preRaceClock-sequenceIndex*step;
  const difficult=focus?.id===gateDifficultHorseId;
  const refusalKey=`gate-refusal-${focus?.id||0}`;
  if(difficult&&local>=290&&local<820&&!commentaryStamp.has(refusalKey)){
    commentaryStamp.add(refusalKey);
    setCommentary(`${focus.id}番${focus.name}、ゲート入りを嫌がっています。係員がゆっくりと促します。`);
  }
  let travel=Math.max(0,Math.min(1,local/850));
  if(difficult){
    if(travel>.34&&travel<.74)travel=.34+Math.abs(Math.sin(local/55))*.035;
    else if(travel>=.74)travel=.34+(travel-.74)/.26*.66;
  }
  const wait=waitingHorsePosition(focus,vx,camY,vw,camH);
  const horseX=wait.x+travel*(gateX-11-wait.x),horseY=wait.y+travel*(camY+35-wait.y)+(difficult&&travel<.8?Math.sin(local/60)*2:0);
  if(focus&&local<900)drawVisionCandidateHorse(horseX,horseY,focus,.34);
  if(difficult&&local<820){ctx.fillStyle="#efb05d";ctx.fillRect(horseX-18,horseY+4,4,8);ctx.fillStyle="#315b84";ctx.fillRect(horseX-19,horseY+11,7,6)}
  ctx.fillStyle="#fff3a6";ctx.font="bold 7px sans-serif";ctx.textAlign="left";
  ctx.fillText(difficult&&local<820?`${focus.id}番、ゲート入りを嫌がる`:`${focus?.id||8}番、枠入り`,vx+8,camY+9);
}

function drawVisionGateBreak(vx,camY,vw,camH){
  const burst=Math.max(0,Math.min(1,(preRaceClock-360)/500));
  const gateW=Math.max(29,Math.min(38,vw*.19)),gateH=Math.max(31,Math.min(41,camH-7));
  const gateX=vx+vw-gateW-9-burst*(vw*.7),gateY=camY+4;
  ctx.fillStyle="#f5f5ed";ctx.fillRect(gateX,gateY,gateW,gateH);
  ctx.strokeStyle="#7f918f";ctx.lineWidth=3;ctx.strokeRect(gateX,gateY,gateW,gateH);
  if(burst>0)horses.forEach((h,i)=>drawVisionCandidateHorse(vx+vw-14+burst*20+(i%3)*5,camY+15+(i%4)*7,h,.34));
  if(burst>0){
    const notable=horses.filter(h=>h.startReaction!=="普通").map(h=>`${h.id}番 ${h.startReaction}`).join("　");
    ctx.fillStyle="#fff3a6";ctx.font="bold 8px sans-serif";ctx.textAlign="center";ctx.fillText(notable||"各馬そろったスタート",vx+vw/2,camY+10);
  }
  if(burst===0){ctx.fillStyle="#fff3a6";ctx.font="bold 8px sans-serif";ctx.textAlign="center";ctx.fillText("8番が入り、全馬収容",vx+vw/2,camY+10)}
}

function assignStartReactions(){
  horses.forEach(h=>{
    const lowDash=Math.max(0,(560-h.dash)/560),lowGate=Math.max(0,(620-h.gateSkill)/620),timidness=Math.max(0,(45-h.temperamentValue)/45);
    const hoodReduction=h.equippedTack==="hood"?.42:1;
    const lateRisk=Math.min(.14,(.012+lowDash*.045+lowGate*.065+timidness*.035)*hoodReduction);
    const roll=raceRandom(),sharpChance=Math.max(.035,Math.min(.18,.055+(h.dash+h.gateSkill-1100)*.00012));
    h.startReaction=roll<lateRisk?"出遅れ":roll>1-sharpChance?"好スタート":"普通";
    h.gateChecked=true;
    if(h.startReaction==="出遅れ")h.temperamentTrouble="出遅れ";
  });
}

function drawHorizontalTrack(){
  ctx.fillStyle="#2d7131";ctx.fillRect(0,0,LOGICAL_WIDTH,logicalHeight);
  const isDirt=raceSurface==="ダート";
  const trace=(lane,color,width)=>{ctx.beginPath();for(let i=0;i<=180;i++){const q=coursePoint(i/180,lane);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y)}ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.stroke()};
  trace(4.5,"#fff8dd",52);trace(4.5,isDirt?"#a87549":"#43943e",43);
  for(let lane=1;lane<=8;lane++)trace(lane,isDirt?"#b77e4e":"#56a34b",1);
  ctx.fillStyle="#185b29";ctx.fillRect(76,72,208,136);
  const visionOrder=order();
  ctx.fillStyle="#0b151d";ctx.fillRect(91,75,178,128);ctx.strokeStyle="#d7c35d";ctx.lineWidth=4;ctx.strokeRect(91,75,178,128);
  ctx.fillStyle="#293b32";ctx.fillRect(97,81,166,21);ctx.fillStyle="#fff3a6";ctx.font="bold 8px sans-serif";ctx.textAlign="center";ctx.fillText("TURF VISION",180,90);ctx.fillText(playerSetup.raceName||"テストレース",180,100);
  ctx.fillStyle=isDirt?"#9a6c43":"#4a9945";ctx.fillRect(97,106,166,45);
  const leaderDist=raceDistance(visionOrder[0]);
  visionOrder.filter(h=>leaderDist-raceDistance(h)<=45).slice(0,3).forEach((h,i)=>drawVisionCandidateHorse(225-(leaderDist-raceDistance(h))*2.4,132+i*4,h,.55));
  visionOrder.slice(0,4).forEach((h,i)=>{const y=164+i*9;ctx.fillStyle=h.color;ctx.fillRect(103,y-7,9,9);ctx.fillStyle="#fff";ctx.font="bold 7px sans-serif";ctx.textAlign="left";ctx.fillText(`${i+1}位`,116,y);ctx.fillStyle="#26342c";ctx.fillRect(145,y-7,108,6);ctx.fillStyle=h.stamina<.3?"#df4b3f":"#53c96b";ctx.fillRect(145,y-7,108*Math.max(.02,h.stamina),6)});
  ctx.fillStyle="#ffe46d";ctx.font="bold 8px sans-serif";ctx.textAlign="left";ctx.fillText("横向きレイアウト TEST",8,14);
  trace(8.7,"#fffdf0",3);
  if(startMarkerVisible())drawMarker(START_PROGRESS,"#35dc5c","START");if(finishMarkerVisible())drawMarker(FINISH_PROGRESS%1,"#ec3d35","GOAL");
}

// レイアウトV2用の着差表示。ゴール後は時計差、道中は実距離差から換算する。
function marginLabel(prev,h){
  if(state==="ready"||raceClock<600)return"--";
  let gap;
  if(prev.finished&&h.finished)gap=Math.max(0,h.finishTime-prev.finishTime)*.0166;
  else gap=Math.max(0,raceDistance(prev)-raceDistance(h));
  if(gap<.15)return"ハナ";
  if(gap<.4)return"アタマ";
  if(gap<.8)return"クビ";
  if(gap<1.6)return"1/2";
  if(gap<2.2)return"3/4";
  if(gap<3.1)return"1";
  if(gap>=24)return"大差";
  const lengths=Math.round(gap/2.4*2)/2;
  return lengths%1?`${Math.floor(lengths)} 1/2`:`${lengths}`;
}

// レイアウトV2：縦画面のまま上から「コース（横長）→ターフビジョン→高低差」を積む。
// ビジョンはコースの外に独立させ、走路とは重ねない。スタミナバーは表示しない。
function drawTrackV2(){
  const isBanei=currentRaceVenue==="帯広";
  const isDirt=raceSurface==="ダート"||isBanei;
  ctx.fillStyle="#0d1a26";ctx.fillRect(0,0,LOGICAL_WIDTH,logicalHeight);
  // コース帯の芝生下地。
  ctx.fillStyle="#2d7131";ctx.fillRect(0,42,360,208);
  for(let i=0;i<44;i++){
    const x=(i*83)%356,y=46+(i*47)%200;
    ctx.fillStyle=i%3?"#245f27":"#347b32";ctx.fillRect(x,y,3,3);
  }
  // 上部のレース銘板。重賞ほど金属装飾を豪華にする。
  const gradeLevel=playerSetup.raceClass==="G1"?3:playerSetup.raceClass==="G2"?2:playerSetup.raceClass==="G3"?1:0;
  const plateBorder=gradeLevel===3?"#ffe36d":gradeLevel===2?"#d7dce2":gradeLevel===1?"#c98d45":"#8aa391";
  ctx.fillStyle="#101a21";ctx.fillRect(0,0,360,31);
  ctx.fillStyle=gradeLevel>=2?"#18273a":"#1a2c25";ctx.fillRect(6,2,348,27);
  ctx.strokeStyle=plateBorder;ctx.lineWidth=gradeLevel===3?3:2;ctx.strokeRect(6,2,348,27);
  if(gradeLevel===3){ctx.strokeStyle="#8e6f20";ctx.lineWidth=1;ctx.strokeRect(10,5,340,21);for(let x=14;x<350;x+=28){ctx.fillStyle="#fff2a3";ctx.fillRect(x,3,3,3)}}
  ctx.fillStyle=plateBorder;ctx.font=`bold ${gradeLevel?10:9}px sans-serif`;ctx.textAlign="center";
  ctx.fillText(playerSetup.raceName||"テストレース",180,13);
  ctx.fillStyle="#f5f1df";ctx.font="bold 8px sans-serif";
  ctx.fillText(`${currentRaceVenue}　${raceSurface}${TOTAL}m　${currentCourseSpec.route}　${playerSetup.going}`,180,24);
  const standY=232;
  ctx.fillStyle="#6e8492";ctx.fillRect(4,standY,352,5);
  ctx.fillStyle="#506574";ctx.fillRect(4,standY+5,352,7);
  ctx.fillStyle="#37475c";ctx.fillRect(4,standY+12,352,10);
  const crowdCount=playerSetup.raceClass==="G1"?230:playerSetup.raceClass==="G2"?180:playerSetup.raceClass==="G3"?135:playerSetup.raceClass==="オープン"?90:45;
  const crowdColors=["#e65b4f","#f0d56a","#5ca6d8","#f2eee0","#7356a8"];
  for(let i=0;i<crowdCount;i++){
    // raceSeedと番号から固定乱数を作り、毎フレームちらつかず不規則に配置する。
    const hash=(Math.imul(i+17,1103515245)+Math.imul(raceSeed+31,12345))>>>0;
    const x=7+(hash%346),row=(hash>>>9)%4,y=standY+3+row*4,size=(hash>>>15)%5===0?3:2;
    ctx.fillStyle=crowdColors[(hash>>>18)%crowdColors.length];
    ctx.fillRect(x,y,size,size+1);
  }
  const straightCourse=currentCourseSpec.route==="直線";
  const trace=(lane,color,width)=>{
    drawingCourseTrace=true;
    ctx.beginPath();
    if(straightCourse){
      const a=coursePoint(START_PROGRESS,lane),b=coursePoint(FINISH_PROGRESS,lane);ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
    }else for(let i=0;i<=180;i++){const q=coursePoint(i/180,lane);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y)}
    if(!straightCourse)ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.stroke();drawingCourseTrace=false;
  };
  trace(4.5,"#f1ead2",46);
  trace(4.5,isDirt?"#a87549":"#43943e",39);
  for(let lane=1;lane<=8;lane++)trace(lane,isDirt?(lane%2?"#c18a58":"#94613d"):(lane%2?"#65ad55":"#378537"),1);
  if(isBanei){
    [{x:131,h:10,label:"第1障害"},{x:238,h:18,label:"第2障害"}].forEach(o=>{
      ctx.fillStyle="#8a603d";ctx.beginPath();ctx.moveTo(o.x-13,155);ctx.lineTo(o.x,155-o.h);ctx.lineTo(o.x+13,155);ctx.fill();
      ctx.fillStyle="#fff3a6";ctx.font="bold 7px sans-serif";ctx.textAlign="center";ctx.fillText(o.label,o.x,174);
    });
  }
  // 内馬場。
  if(!straightCourse){
    ctx.beginPath();
    for(let i=0;i<=120;i++){const q=coursePoint(i/120,9.4);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y)}
    ctx.closePath();ctx.fillStyle="#1e5d28";ctx.fill();
  }
  const profile=trackProfile();
  if(["museum","pond","sea"].includes(profile.facility)){
    ctx.fillStyle="#4d9dc1";ctx.fillRect(96,120,34,12);ctx.fillRect(104,116,18,4);
  }
  ctx.fillStyle="#9fd6a0";ctx.font="bold 9px sans-serif";ctx.textAlign="center";
  trace(8.7,"#fffdf0",2);
  if(startMarkerVisible())drawMarker(START_PROGRESS,"#35dc5c","START");
  if(finishMarkerVisible())drawMarker(FINISH_PROGRESS%1,"#ec3d35","GOAL");

  // 内馬場ターフビジョン。下側にあった中継映像をここへ統合する。
  if(!straightCourse){
    const innerRail=[];
    for(let i=0;i<120;i++)innerRail.push(coursePoint(i/120,8.7));
    const minX=Math.min(...innerRail.map(p=>p.x)),maxX=Math.max(...innerRail.map(p=>p.x));
    const minY=Math.min(...innerRail.map(p=>p.y)),maxY=Math.max(...innerRail.map(p=>p.y));
    const innerW=maxX-minX,innerH=maxY-minY;
    const mw=Math.floor(innerW*.68),mh=Math.floor(innerH*.58);
    const mx=Math.round((minX+maxX-mw)/2),my=Math.round((minY+maxY-mh)/2);
    const centerOrder=order(),front=Math.max(...centerOrder.map(h=>raceDistance(h)));
    const screenX=mx+3,screenY=my+20,screenW=mw-6,screenH=mh-23;
    ctx.fillStyle="#111a20";ctx.fillRect(mx,my,mw,mh);ctx.strokeStyle=plateBorder;ctx.lineWidth=2;ctx.strokeRect(mx,my,mw,mh);
    ctx.fillStyle="#263a2e";ctx.fillRect(mx+2,my+2,mw-4,16);
    ctx.fillStyle="#fff3a6";ctx.font="bold 8px sans-serif";ctx.textAlign="center";ctx.fillText("TURF VISION　中継映像",mx+mw/2,my+12);
    if(state==="runout"||state==="finished"){
      const winner=centerOrder[0];
      ctx.fillStyle="#10151a";ctx.fillRect(screenX,screenY,screenW,screenH);
      ctx.fillStyle="#d83232";ctx.fillRect(mx+mw-55,my+24,43,21);ctx.fillStyle="#fff";ctx.font="bold 14px sans-serif";ctx.fillText("確定",mx+mw-34,my+40);
      drawVisionCandidateHorse(mx+34,my+Math.min(61,mh-33),winner,.58);
      centerOrder.slice(0,3).forEach((h,index)=>{const y=my+58+index*13;ctx.fillStyle="#e8edf0";ctx.font="bold 8px sans-serif";ctx.textAlign="left";ctx.fillText(`${index+1}着 ${h.id}番`,mx+mw*.53,y);ctx.fillStyle=index?"#cfb96f":"#ffe36d";ctx.textAlign="right";ctx.fillText(index?marginLabel(centerOrder[index-1],h):formatTime(h.finishTime),mx+mw-8,y)});
    }else if(state==="parade"){
      ctx.fillStyle=isDirt?"#9a6c43":"#4a9445";ctx.fillRect(screenX,screenY,screenW,screenH);
      horses.forEach((h,i)=>{
        const travel=Math.max(0,Math.min(1,(preRaceClock-i*300)/1800));
        if(travel<=0)return;
        const target=waitingHorsePosition(h,screenX,screenY,screenW,screenH);
        const entryY=screenY+15+(i%3)*Math.max(8,screenH*.15);
        drawVisionCandidateHorse(screenX+12+(target.x-screenX-12)*travel,entryY+(target.y-entryY)*travel,h,.36);
      });
    }else if(state==="gates"){
      ctx.fillStyle=isDirt?"#9a6c43":"#4a9445";ctx.fillRect(screenX,screenY,screenW,screenH);
      drawVisionGate(screenX,screenY,screenW,screenH);
    }else if(state==="gateBreak"){
      ctx.fillStyle=isDirt?"#9a6c43":"#4a9445";ctx.fillRect(screenX,screenY,screenW,screenH);
      drawVisionGateBreak(screenX,screenY,screenW,screenH);
    }else{
      ctx.fillStyle=isDirt?"#9a6c43":"#4a9445";ctx.fillRect(screenX,screenY,screenW,screenH);
      const visible=centerOrder.filter(h=>front-raceDistance(h)<=125).slice(0,8);
      visible.forEach((h,index)=>{
        const gap=front-raceDistance(h),x=screenX+screenW-18-gap*Math.max(.75,screenW/150),y=screenY+15+(index%4)*Math.max(10,screenH*.2);
        drawVisionCandidateHorse(x,y,h,.36);
      });
    }
  }

  // コース直下の実況帯（最新4行）。
  const commentaryY=254;
  ctx.fillStyle="#071018";ctx.fillRect(4,commentaryY,352,74);
  ctx.strokeStyle="#d7c35d";ctx.lineWidth=2;ctx.strokeRect(4,commentaryY,352,74);
  ctx.fillStyle="#35251c";ctx.fillRect(12,commentaryY+10,17,5);ctx.fillRect(11,commentaryY+14,3,10);
  ctx.fillStyle="#d8a06e";ctx.fillRect(13,commentaryY+15,14,15);
  ctx.fillStyle="#25201d";ctx.fillRect(16,commentaryY+20,2,2);ctx.fillRect(23,commentaryY+20,2,2);
  ctx.fillStyle="#a96644";ctx.fillRect(20,commentaryY+23,2,2);
  ctx.fillStyle="#6f2d28";ctx.fillRect(17,commentaryY+27,7,Math.floor(raceClock/260)%2===0?2:1);
  ctx.fillStyle="#172d4b";ctx.fillRect(10,commentaryY+32,20,29);
  ctx.fillStyle="#f3f0df";ctx.fillRect(17,commentaryY+33,6,13);
  ctx.fillStyle="#294a73";ctx.fillRect(11,commentaryY+34,6,18);ctx.fillRect(23,commentaryY+34,6,18);
  ctx.fillStyle="#a93632";ctx.fillRect(19,commentaryY+38,2,10);
  ctx.fillStyle="#d7c35d";ctx.fillRect(26,commentaryY+44,7,2);
  const commentaryLines=wrappedCommentaryLines(commentaryHistory);
  ctx.font="bold 11px sans-serif";ctx.textAlign="left";
  commentaryLines.forEach((line,index)=>{
    const aboutPlayer=line.includes(playerSetup.horseName)||line.includes("愛馬");
    ctx.fillStyle=aboutPlayer?"#ffe45c":"#f4f6f2";
    ctx.fillText(line,38,commentaryY+15+index*17);
  });

  // 下側は順位・スタミナ情報専用。中継映像は内馬場へ移動済み。
  const visionOrder=order(),leader=visionOrder[0];
  const vx=4,vy=330,vw=352,vh=228;
  ctx.fillStyle="#101a21";ctx.fillRect(vx,vy,vw,vh);
  ctx.strokeStyle="#d7c35d";ctx.lineWidth=3;ctx.strokeRect(vx,vy,vw,vh);
  ctx.fillStyle="#263a2e";ctx.fillRect(vx+3,vy+3,vw-6,18);
  ctx.fillStyle="#fff3a6";ctx.font="bold 12px sans-serif";ctx.textAlign="center";
  ctx.fillText("順位・スタミナ",180,vy+16);
  const camY=vy+22,camH=0;
  const leaderDist=raceDistance(leader);
  // 馬名タグ：先頭と自分の馬（仕様：ビジョンに愛馬の馬番と馬名を表示）。
  // 全頭順位ボード：枠色チップ＋馬番＋馬名フル表示＋着差。
  const boardY=camY+4;
  visionOrder.forEach((h,index)=>{
    const y=boardY+12+index*14;
    if(h.player){ctx.fillStyle="#5b451d";ctx.fillRect(vx+3,y-12,vw-6,14)}
    const prevRank=visionRanks.get(h.id)??index+1;
    const arrow=prevRank>index+1?"▲":prevRank<index+1?"▼":"・";
    ctx.font="bold 12px sans-serif";ctx.textAlign="left";
    ctx.fillStyle=h.player?"#ffe56b":"#eef4ed";ctx.fillText(`${index+1}位`,vx+8,y);
    ctx.fillStyle=arrow==="▲"?"#7be08a":arrow==="▼"?"#e08a7b":"#7d919e";ctx.fillText(arrow,vx+34,y);
    ctx.fillStyle=h.color;ctx.fillRect(vx+48,y-11,13,13);
    if(h.id===1){ctx.strokeStyle="#666";ctx.lineWidth=1;ctx.strokeRect(vx+48,y-11,13,13)}
    ctx.fillStyle=numberTextColor(h.id);ctx.font="bold 10px sans-serif";ctx.textAlign="center";
    ctx.fillText(h.id,vx+54,y-1);
    ctx.font="bold 12px sans-serif";ctx.textAlign="left";
    ctx.fillStyle=h.player?"#ffe56b":"#eef4ed";ctx.fillText(h.name,vx+66,y);
    ctx.textAlign="right";ctx.fillStyle=h.player?"#ffe56b":"#a9c2b4";
    ctx.fillText(index===0?(h.finished?formatTime(h.finishTime):""):marginLabel(visionOrder[index-1],h),vx+vw-8,y);
  });
  if(raceClock-visionRankStamp>700){visionOrder.forEach((h,i)=>visionRanks.set(h.id,i+1));visionRankStamp=raceClock}
  // フッター：タイム・1000m通過・残り距離・現在区間。
  const footY=vy+vh-31;
  ctx.fillStyle="#263a2e";ctx.fillRect(vx+3,footY,vw-6,28);
  const remaining=Math.max(0,Math.ceil(TOTAL-Math.min(TOTAL,leaderDist)));
  const grad=courseGradient(leader.progress);
  ctx.fillStyle="#fff3a6";ctx.font="bold 11px sans-serif";ctx.textAlign="center";
  ctx.fillText(`残り${remaining}m　TIME ${formatTime(raceClock)}　1000m ${split1000Time?formatTime(split1000Time):"--:--.-"}　${grad.type==="up"?"▲上り":grad.type==="down"?"▼下り":"平坦"}`,180,footY+11);
  ctx.font="bold 9px sans-serif";
  ctx.fillText(`実測 ${measuredPace}　基準 ${formatTime(playerSetup.benchmarkTime||playerSetup.baseTime)}　レコード ${formatTime(playerSetup.recordTime||playerSetup.baseTime*.965)}　${playerSetup.weather}/${playerSetup.going}`,180,footY+23);

  // 高低差・全馬位置（維持）。
  const ex=4,ey=564,ew=352,eh=56;
  ctx.fillStyle="#e8edcf";ctx.fillRect(ex,ey,ew,eh);
  ctx.strokeStyle="#d7c35d";ctx.lineWidth=3;ctx.strokeRect(ex,ey,ew,eh);
  ctx.fillStyle="#3c5220";ctx.font="bold 10px sans-serif";ctx.textAlign="left";
  ctx.fillText("高低差・全馬位置",ex+6,ey+11);
  ctx.textAlign="right";ctx.fillStyle="#6b4c14";
  ctx.fillText(`現在:${grad.label}　${currentRaceVenue}${raceSurface} 高低差${trackProfile().elevation}m`,ex+ew-6,ey+11);
  ctx.beginPath();
  for(let i=0;i<=64;i++){
    const n=i/64,progress=START_PROGRESS+n*TOTAL/LAP;
    const x=ex+8+n*(ew-16),y=ey+eh-8-(courseElevation(progress)-6)*1.35;
    i?ctx.lineTo(x,y):ctx.moveTo(x,y);
  }
  ctx.strokeStyle="#5d773c";ctx.lineWidth=2;ctx.stroke();
  horses.forEach(h=>{
    const n=Math.max(0,Math.min(1,raceDistance(h)/TOTAL));
    const x=ex+8+n*(ew-16),y=ey+eh-8-(courseElevation(h.progress)-6)*1.35;
    if(h.player){ctx.strokeStyle="#b8860b";ctx.lineWidth=2;ctx.strokeRect(Math.round(x-5),Math.round(y-5),10,10)}
    ctx.fillStyle=h.color;ctx.fillRect(Math.round(x-4),Math.round(y-4),8,8);
    ctx.fillStyle=numberTextColor(h.id);ctx.font="bold 8px sans-serif";ctx.textAlign="center";
    ctx.fillText(h.id,Math.round(x),Math.round(y+3));
  });
  ctx.textAlign="center";
}

function drawTrack() {
  if(layoutV2){drawTrackV2();return;}
  if(horizontalLayout){drawHorizontalTrack();return;}
  const isDirt = raceSurface === "ダート";
  ctx.fillStyle = "#2d7131";
  ctx.fillRect(0, 0, LOGICAL_WIDTH, logicalHeight);

  for (let i = 0; i < 60; i++) {
    const x = (i * 83) % 356;
    const y = (i * 47) % 490;
    ctx.fillStyle = isDirt
      ? (i % 3 ? "#49682c" : "#607e3b")
      : (i % 3 ? "#245f27" : "#347b32");
    ctx.fillRect(x, y, 3, 3);
  }

  const traceCourse=(lane,color,width)=>{
    ctx.beginPath();
    for(let i=0;i<=180;i++){
      const q=coursePoint(i/180,lane);
      if(i===0)ctx.moveTo(q.x,q.y);else ctx.lineTo(q.x,q.y);
    }
    ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.stroke();
  };
  traceCourse(4.5,"#f1ead2",59);
  traceCourse(4.5,isDirt?"#a87549":"#43943e",49);
  for(let lane=1;lane<=8;lane++)traceCourse(lane,isDirt?(lane%2?"#c18a58":"#94613d"):(lane%2?"#65ad55":"#378537"),1);

  // 各場の内馬場施設を航空写真風にドット化。
  ctx.fillStyle="#1e5d28";ctx.fillRect(76,126,208,248);
  ctx.fillStyle="#7ca05d";ctx.fillRect(100,167,160,54);
  ctx.fillStyle="#d8d0b8";ctx.fillRect(112,182,72,31);
  ctx.fillStyle="#64737b";ctx.fillRect(118,188,60,19);
  ctx.fillStyle="#b88b62";ctx.fillRect(197,174,44,35);
  ctx.fillStyle="#557b45";ctx.fillRect(107,270,55,62);
  ctx.strokeStyle="#d9c592";ctx.lineWidth=3;ctx.strokeRect(113,278,42,46);
  ctx.fillStyle="#9b7655";ctx.fillRect(196,267,54,37);
  ctx.fillStyle="#6f9664";ctx.fillRect(202,273,42,25);
  const profile=trackProfile();
  if(profile.facility==="sea"){ctx.fillStyle="#55a9c8";ctx.fillRect(92,337,176,18)}
  if(profile.facility==="fkc"){ctx.fillStyle="#f1d15d";ctx.font="bold 18px sans-serif";ctx.fillText("FKC",180,320)}
  if(profile.facility==="pond"){ctx.fillStyle="#4d9dc1";ctx.fillRect(103,287,58,34)}
  if(profile.facility==="long"){ctx.fillStyle="#bd9b70";ctx.fillRect(84,146,192,10)}
  if(profile.facility==="garden"){ctx.fillStyle="#d97c93";for(let x=102;x<250;x+=18)ctx.fillRect(x,315,8,8)}
  if(["門別","盛岡","浦和","船橋","大井","川崎","金沢","名古屋","園田","高知","佐賀"].includes(currentRaceVenue)){
    ctx.fillStyle=currentRaceVenue==="盛岡"?"#416b39":"#d7c8a1";
    ctx.fillRect(126,292,108,22);
    ctx.fillStyle="#263d32";ctx.font="bold 11px sans-serif";ctx.textAlign="center";
    ctx.fillText(currentRaceVenue+"競馬場",180,307);
    if(["大井","川崎","船橋","浦和"].includes(currentRaceVenue)){
      ctx.fillStyle="#87989e";ctx.fillRect(112,320,136,13);ctx.fillStyle="#cfd8d8";for(let x=116;x<244;x+=14)ctx.fillRect(x,322,8,7);
    }
    if(currentRaceVenue==="門別"){ctx.fillStyle="#efe8d2";ctx.fillRect(105,321,52,14);ctx.fillRect(203,321,52,14)}
    if(currentRaceVenue==="金沢"){ctx.fillStyle="#e8bb45";ctx.fillRect(151,322,58,12);ctx.fillStyle="#b84942";ctx.fillRect(173,315,14,26)}
  }
  // 長いホーム直線沿いのスタンド。走路より外へ置き、馬とは重ねない。
  ctx.fillStyle="#c9d3d3";ctx.fillRect(352,112,7,266);
  ctx.fillStyle="#506574";
  for(let y=120;y<370;y+=15)ctx.fillRect(353,y,5,8);
  ctx.fillStyle="#e6e0cb";ctx.fillRect(344,108,7,274);
  const crowdCount=["G1","G2","G3"].includes(playerSetup.raceClass)?42:playerSetup.raceClass==="オープン"?25:12;
  const crowdColors=["#e65b4f","#f0d56a","#5ca6d8","#f2eee0","#7356a8"];
  for(let i=0;i<crowdCount;i++){
    const x=345+(i%3)*4,y=116+((i*17)%252);
    ctx.fillStyle=crowdColors[i%crowdColors.length];ctx.fillRect(x,y,3,4);
  }
  const player=horses.find(h=>h.player),visionOrder=order();
  ctx.fillStyle="#101a21";ctx.fillRect(68,132,224,211);ctx.strokeStyle="#d7c35d";ctx.lineWidth=4;ctx.strokeRect(68,132,224,211);
  ctx.fillStyle="#263a2e";ctx.fillRect(75,139,210,26);
  ctx.fillStyle="#fff3a6";ctx.font="bold 8px sans-serif";ctx.textAlign="center";
  ctx.fillText("TURF VISION",180,148);
  ctx.font="bold 10px sans-serif";ctx.fillText(playerSetup.raceName||document.querySelector("#raceNameTitle")?.textContent||"レース名",180,161);
  // 先頭を基準に、カメラ範囲内（約65m）へ入っている馬を実際の差で配置する。
  ctx.fillStyle=raceSurface==="ダート"?"#9a6c43":"#3e8e3e";ctx.fillRect(76,170,208,35);
  const leaderVisionDistance=raceDistance(visionOrder[0]);
  const visibleVisionHorses=visionOrder.filter(h=>leaderVisionDistance-raceDistance(h)<=105).slice(0,5);
  visibleVisionHorses.forEach((h,i)=>{
    const lead=Math.max(0,leaderVisionDistance-raceDistance(h));
    const x=Math.max(84,Math.min(257,Math.round(252-lead*2.55)));
    const y=176+(i%3)*8,legPhase=(Math.floor(raceClock/180)+h.id)%2;
    ctx.fillStyle=h.player?"#ffe15a":"#bd7137";ctx.fillRect(x,y,18,7);ctx.fillRect(x+14,y-5,7,7);ctx.fillRect(x-5,y+1,7,3);
    ctx.fillRect(x+(legPhase?3:1),y+7,3,5);ctx.fillRect(x+(legPhase?12:14),y+7,3,5);
    ctx.fillStyle=h.color;ctx.fillRect(x+6,y+1,7,5);ctx.fillStyle=numberTextColor(h.id);ctx.font="bold 5px sans-serif";ctx.fillText(h.id,x+9,y+6);
  });
  visionOrder.forEach((h,index)=>{
    const y=220+index*14;
    if(h.player){ctx.fillStyle="#5b451d";ctx.fillRect(75,y-10,210,13)}
    ctx.fillStyle=h.color;ctx.fillRect(79,y-9,11,11);
    ctx.fillStyle=numberTextColor(h.id);ctx.font="bold 7px sans-serif";ctx.fillText(h.id,84,y);
    const previous=visionRanks.get(h.id)??index+1,arrow=previous>index+1?"▲":previous<index+1?"▼":"・";
    ctx.fillStyle=h.player?"#ffe56b":"#eef4ed";ctx.font="bold 8px sans-serif";ctx.textAlign="left";ctx.fillText(`${index+1}位${arrow} ${h.name.slice(0,8)}`,96,y);
    ctx.fillStyle="#26342c";ctx.fillRect(214,y-8,65,7);ctx.fillStyle=h.stamina<.3?"#df4b3f":h.stamina<.55?"#e4bf3f":"#53c96b";ctx.fillRect(214,y-8,65*Math.max(.02,h.stamina),7);
  });
  if(raceClock-visionRankStamp>700){visionOrder.forEach((h,i)=>visionRanks.set(h.id,i+1));visionRankStamp=raceClock}
  ctx.textAlign="center";

  // 高低差図をターフビジョン直下へ小さく配置し、全馬の現在位置を重ねる。
  const elevationX=68,elevationY=343,elevationW=224,elevationH=31;
  ctx.fillStyle="#e8edcf";ctx.fillRect(elevationX,elevationY,elevationW,elevationH);
  ctx.strokeStyle="#d7c35d";ctx.lineWidth=3;ctx.strokeRect(elevationX,elevationY,elevationW,elevationH);
  ctx.beginPath();
  for(let i=0;i<=48;i++){
    const n=i/48,progress=START_PROGRESS+n*TOTAL/LAP;
    const x=elevationX+5+n*(elevationW-10);
    const y=elevationY+22-(courseElevation(progress)-8)*.72;
    if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
  }
  ctx.strokeStyle="#5d773c";ctx.lineWidth=3;ctx.stroke();
  horses.forEach(h=>{
    const n=Math.max(0,Math.min(1,raceDistance(h)/TOTAL));
    const x=elevationX+5+n*(elevationW-10);
    const y=elevationY+22-(courseElevation(h.progress)-8)*.72;
    ctx.fillStyle=h.color;ctx.fillRect(Math.round(x-3),Math.round(y-3),7,7);
    if(h.player){ctx.strokeStyle="#ffdf39";ctx.lineWidth=2;ctx.strokeRect(Math.round(x-4),Math.round(y-4),9,9)}
    ctx.fillStyle=numberTextColor(h.id);ctx.font="bold 5px sans-serif";ctx.textAlign="center";ctx.fillText(h.id,Math.round(x),Math.round(y+2));
  });

  // ターフビジョンは内柵より大きいため、柵を最後に重ねて一周つなげる。
  traceCourse(8.7,"#fffdf0",3);
  for(let i=0;i<36;i++){
    const post=coursePoint(i/36,8.7);
    ctx.fillStyle="#fffdf0";ctx.fillRect(Math.round(post.x-1),Math.round(post.y-1),3,3);
  }

  if(startMarkerVisible())drawMarker(START_PROGRESS, "#35dc5c", "START");
  if(finishMarkerVisible())drawMarker(FINISH_PROGRESS % 1, "#ec3d35", "GOAL");
  ctx.fillStyle = "#ffe068";
  ctx.font = "bold 9px sans-serif";
  ctx.textAlign = "center";
  ctx.fillStyle = "#fff3c5";
  ctx.fillText("外", 25, 244);
  ctx.fillText("内", 62, 244);
}

function ellipse(cx, cy, rx, ry, color) {
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
}

function strokeEllipse(cx, cy, rx, ry, color, width) {
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.stroke();
}

function drawMarker(progress, color, label) {
  const inner = coursePoint(progress, 8.7);
  const outer = coursePoint(progress, -.3);
  const p = coursePoint(progress, 4.2);
  // コースの接線に対して直角な一本線にする。
  // レーンごとの形状差から端点を直接結ぶと斜めに見えるため、
  // 中心点と進行角度から同一方向へ線を伸ばす。
  const cx=(inner.x+outer.x)/2,cy=(inner.y+outer.y)/2;
  const nx=-Math.sin(p.angle),ny=Math.cos(p.angle);
  const halfLength=Math.hypot(outer.x-inner.x,outer.y-inner.y)/2+3;
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.lineCap = "butt";
  ctx.beginPath();
  if(Math.abs(nx)>=Math.abs(ny)){
    ctx.moveTo(Math.round(cx-halfLength),Math.round(cy));ctx.lineTo(Math.round(cx+halfLength),Math.round(cy));
  }else{
    ctx.moveTo(Math.round(cx),Math.round(cy-halfLength));ctx.lineTo(Math.round(cx),Math.round(cy+halfLength));
  }
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.fillRect(Math.round(cx - 2), Math.round(cy - 7), 5, 12);
  ctx.fillStyle = "#05080d";
  ctx.font = "bold 8px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(label, cx, cy + 15);
}

function draw() {
  drawTrack();
  [...horses].sort((a, b) => b.lane - a.lane).forEach(h => drawPixelHorse(h, coursePoint(h.progress, h.lane)));
  drawWeather();
  drawCrowdCheer();
}

function drawCrowdCheer(){
  const visionOrder=order(),leader=visionOrder[0];
  if(!leader||state!=="running")return;
  const travelled=raceDistance(leader),profile=trackProfile();
  const distanceToFinishLine=((FINISH_PROGRESS-leader.progress)%1+1)%1*LAP;
  // 周回ごとのホーム直線に入った時だけ、スタンドから歓声を出す。
  if(distanceToFinishLine>profile.straight*1.04)return;
  const ratio=raceDistance(leader)/TOTAL;
  const calls=ratio>.82?["差せー！","粘れー！","そのまま！","伸びろー！","届いてくれ！","逃げ切れ！","並んだ！","もう少し！","いけー！","突き抜けろ！"]:ratio>.62?["外から来た！","内を突け！","前が開いた！","進路を取れ！","動き出した！","差を詰めろ！","いい脚だ！","馬群を割れ！"]:["いいぞー！","前を追え！","落ち着いて！","いい手応え！","まだ我慢！","行けるぞ！","頑張れー！"];
  const gradeLevel=playerSetup.raceClass==="G1"?4:playerSetup.raceClass==="G2"?3:playerSetup.raceClass==="G3"?2:playerSetup.raceClass==="オープン"?1:0;
  const straightVisit=Math.floor(Math.max(0,travelled)/LAP)+1;
  const excitement=Math.min(5,gradeLevel+Math.min(2,straightVisit-1)+(ratio>.82?1:0));
  const cycles=[4300,3400,2700,2100,1650,1300],cycle=cycles[excitement],visibleFor=Math.min(2600,cycle*.72),slot=Math.floor(cheerClock/cycle);
  if(cheerClock%cycle>=visibleFor)return;
  // 吹き出しの尻尾を下側スタンドへ向ける。格が高いほど同時表示を増やす。
  const spots=layoutV2
    ?[{x:7,y:218,w:104},{x:128,y:218,w:104},{x:249,y:218,w:104}]
    :[{x:226,y:54,w:108},{x:232,y:96,w:102},{x:218,y:220,w:116},{x:225,y:285,w:109},{x:216,y:350,w:118}];
  const bubbleCount=layoutV2?Math.min(3,1+Math.floor(excitement/2)):1;
  ctx.save();
  for(let n=0;n<bubbleCount;n++){
    const spot=spots[(slot+n+raceSeed)%spots.length],call=calls[(slot*7+n*3+raceSeed)%calls.length];
    ctx.shadowColor="#000b";ctx.shadowBlur=0;ctx.shadowOffsetX=2;ctx.shadowOffsetY=2;
    ctx.fillStyle="#ffffff";ctx.strokeStyle="#262015";ctx.lineWidth=2;
    ctx.fillRect(spot.x,spot.y,spot.w,19);ctx.strokeRect(spot.x,spot.y,spot.w,19);
    ctx.beginPath();
    if(layoutV2){const tx=spot.x+spot.w/2;ctx.moveTo(tx-5,spot.y+19);ctx.lineTo(tx,247);ctx.lineTo(tx+5,spot.y+19)}
    else{ctx.moveTo(spot.x+spot.w,spot.y+7);ctx.lineTo(349,spot.y+12);ctx.lineTo(spot.x+spot.w,spot.y+17)}
    ctx.closePath();ctx.fill();ctx.stroke();
    ctx.shadowColor="transparent";ctx.fillStyle="#111";ctx.font="bold 10px sans-serif";ctx.textAlign="center";ctx.fillText(call,spot.x+spot.w/2,spot.y+14);
  }
  ctx.restore();
}

function drawWeather(){
  if(!["雨","大雨","雪"].includes(playerSetup.weather))return;
  const snow=playerSetup.weather==="雪";
  const count=snow?34:playerSetup.weather==="大雨"?75:48;
  ctx.save();
  // レイアウトV2ではビジョン・高低差パネルに雨雪を重ねず、コース帯だけに降らせる。
  if(layoutV2){ctx.beginPath();ctx.rect(0,20,360,232);ctx.clip();}
  ctx.globalAlpha=snow?.9:.68;
  ctx.strokeStyle=snow?"#ffffff":"#bce8ff";
  ctx.fillStyle="#ffffff";
  ctx.lineWidth=snow?1:2;
  for(let i=0;i<count;i++){
    const x=(i*47+(weatherClock*.035*(snow?.35:1)))%380-10;
    const y=(i*83+(weatherClock*.06*(snow?.45:1)))%530-15;
    if(snow){
      const size=2+(i%3);
      ctx.fillRect(Math.round(x),Math.round(y),size,size);
    }else{
      ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-4,y+11);ctx.stroke();
    }
  }
  ctx.restore();
}

function renderRanking() {
  rankingEl.innerHTML = order().map((h, i) => `
    <div class="runner ${i === 0 ? "leader" : ""}">
      <span class="num" style="background:${h.color};color:${numberTextColor(h.id)};border:1px solid ${h.id === 1 ? "#777" : h.color}">${h.id}</span>
      <strong>${i + 1}位 ${h.name}</strong>
      <small class="running-style">脚質：${h.style}　単勝 ${h.odds.toFixed(1)}倍</small>
      <small>能力 ${h.ability}　${h.popularity}番人気</small>
      <small>スタミナ ${Math.round(h.stamina * 100)}%</small>
      <div class="stamina ${h.stamina < .22 ? "danger" : h.stamina < .45 ? "low" : ""}">
        <span style="width:${Math.max(2, Math.round(h.stamina * 100))}%"></span>
      </div>
      ${h.finished ? `<small>走破 ${formatTime(h.finishTime)}</small>` : ""}
    </div>
  `).join("");
}

function loop(time) {
  if (!lastTime) lastTime = time;
  const realDt = Math.min(40, time - lastTime);
  const simulationDt = realDt * BASE_PLAYBACK_RATE * multiplier;
  const clockDt = simulationDt;
  lastTime = time;
  // 雨雪はレース倍速と切り離し、ゲート演出中から一定速度で動かす。
  if(state!=="paused"&&state!=="ready"&&state!=="finished")weatherClock+=realDt;
  if(state==="parade"||state==="gates"||state==="gateBreak"){
    preRaceClock+=realDt;
    if(state==="parade"||state==="gates")waitingMotionClock+=realDt;
    draw();
  } else if (state === "running") {
    cheerClock += realDt;
    simulationAccumulator += simulationDt;
    while (simulationAccumulator >= 16 && state === "running") {
      update(16, 16);
      simulationAccumulator -= 16;
    }
    draw();
    renderRanking();
  } else if(state==="runout"){
    updateRunout(simulationDt);
    draw();
  }
  raf = requestAnimationFrame(loop);
}

function beginRaceAfterGate(){
  if(state!=="gateBreak")return;
  state="running";pauseButton.disabled=false;phaseEl.textContent="スタート";
  gateSkipButton.hidden=true;
  speedButton.hidden=false;
  const late=horses.filter(h=>h.startReaction==="出遅れ"),sharp=horses.filter(h=>h.startReaction==="好スタート");
  setCommentary(late.length
    ? `スタート！ ${late.map(h=>`${h.id}番${h.name}`).join("、")}は出遅れ！`
    : sharp.length?`スタート！ ${sharp.map(h=>`${h.id}番${h.name}`).join("、")}が好スタート！`
    : racePace.escapeCount>=2?`スタート！ 逃げ${racePace.escapeCount}頭が先手を争います！`:"スタート！ 各馬そろった飛び出しです。");
  lastTime=0;
}

startButton.addEventListener("click", () => {
  if (state === "ready") {
    state = "parade";
    preRaceClock=0;
    startButton.disabled = true;
    pauseButton.disabled = true;
    gateSkipButton.hidden = false;
    phaseEl.textContent = "本馬場入場";
    setCommentary("各馬がパドックを後にして、本馬場へ入ってきました。");
    lastTime=0;raf=requestAnimationFrame(loop);
    gateStartTimer=setTimeout(()=>{
      if(state!=="parade")return;
      state="gates";preRaceClock=0;phaseEl.textContent="全馬ゲートイン";
      const difficultHorse=horses.find(h=>(h.temperamentValue>=65||h.temperamentValue<=35)&&h.temperamentRoll<.58);
      gateDifficultHorseId=difficultHorse?.id??null;
      setCommentary("各馬、順番にゲートへ向かいます。");
      gateStartTimer=setTimeout(()=>{
        if(state!=="gates")return;
        assignStartReactions();
        state="gateBreak";preRaceClock=0;phaseEl.textContent="全馬収容";
        gateSkipButton.hidden=true;
        setCommentary("全馬、枠内に収まりました。スタートを待ちます。");
        gateStartTimer=setTimeout(beginRaceAfterGate,900);
      },8100);
    },5000);
  }
});

gateSkipButton.addEventListener("click",()=>{
  if(state!=="parade"&&state!=="gates")return;
  clearTimeout(gateStartTimer);
  assignStartReactions();
  state="gateBreak";preRaceClock=0;phaseEl.textContent="全馬収容";
  gateSkipButton.hidden=true;
  setCommentary("ゲート入りをスキップしました。全馬収容、スタートを待ちます。");
  gateStartTimer=setTimeout(beginRaceAfterGate,700);
});

raceTestBackButton.addEventListener("click",()=>{
  clearTimeout(gateStartTimer);
  state="ready";
  gateSkipButton.hidden=true;
  speedButton.hidden=true;
  window.dispatchEvent(new CustomEvent("dotkeiba:test-back"));
});

pauseButton.addEventListener("click", () => {
  state = state === "paused" ? "running" : "paused";
  pauseButton.textContent = state === "paused" ? "再開" : "一時停止";
  phaseEl.textContent = state === "paused" ? "停止中" : "レース中";
});

speedButton.addEventListener("click", () => {
  const currentIndex=PLAYBACK_RATES.indexOf(multiplier);
  multiplier=PLAYBACK_RATES[(currentIndex+1)%PLAYBACK_RATES.length];
  speedButton.textContent=`レース速度：${multiplier===1?"通常":`${multiplier}倍`}`;
});

resetButton.addEventListener("click", resetRace);
window.addEventListener("dotkeiba:auto-start",()=>{if(state==="ready")startButton.click()});
winnerReplayButton.addEventListener("click",()=>{
  resetRace();
  state="running";
  startButton.disabled=true;
  pauseButton.disabled=false;
  speedButton.hidden=false;
  phaseEl.textContent="リプレイ";
  setCommentary("保存された展開でレースを再現します。",true);
  lastTime=0;
  raf=requestAnimationFrame(loop);
});
favoriteRaceButton.addEventListener("click",()=>{
  if(!pendingResultDetail)return;
  window.dispatchEvent(new CustomEvent("dotkeiba:favorite",{detail:{
    raceName:playerSetup.raceName||document.querySelector("#raceNameTitle").textContent,
    course:`${currentRaceVenue} ${raceSurface}${TOTAL}m`,
    weather:playerSetup.weather,going:playerSetup.going,
    winnerTime:pendingResultDetail.winnerTime,
    seed:raceSeed,setup:{...playerSetup},order:pendingResultDetail.order
  }}));
});
showResultButton.addEventListener("click",()=>{
  if(!pendingResultDetail||resultDispatchedForRace)return;
  if(archiveReplay){
    window.dispatchEvent(new CustomEvent("dotkeiba:archive-close"));
    return;
  }
  resultDispatchedForRace=true;
  window.dispatchEvent(new CustomEvent("dotkeiba:finished",{detail:pendingResultDetail}));
});
window.addEventListener("dotkeiba:prepare", event => {
  playerSetup = { ...playerSetup, ...event.detail };
  archiveReplay=!!event.detail.archiveReplay;
  horizontalLayout=!!event.detail.horizontalLayout;
  layoutV2=event.detail.layoutV2!==undefined?!!event.detail.layoutV2:!horizontalLayout;
  configureCanvas(layoutV2?622:horizontalLayout?280:500);
  document.body.classList.toggle("horizontal-race-test",horizontalLayout);
  document.body.classList.toggle("race-layout2",layoutV2);
  raceSeed = Number.isFinite(event.detail.replaySeed)
    ? event.detail.replaySeed
    : ((Date.now() ^ Math.floor(event.detail.ability * 1009) ^ event.detail.distance) >>> 0) || 1;
  resultDispatchedForRace = false;
  raceSurface = event.detail.surface || "芝";
  currentRaceVenue = event.detail.venue || "東京";
  courseAuditMode=!!event.detail.courseAuditMode;
  raceDirectionOverride=event.detail.direction||null;
  TOTAL = event.detail.distance || 2400;
  configureCourseDistance();
  BASE_PROGRESS_PER_MS = (TOTAL / LAP) / (event.detail.baseTime || TOTAL * 62);
  resetRace();
});

resetRace();

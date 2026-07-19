const LEGACY_SAVE_KEY = "dotKeibaTrialV3";
const SAVE_KEY_PREFIX = "dotKeibaTrialV3Slot";
const ACTIVE_SLOT_KEY = "dotKeibaActiveSaveSlot";
const SAVE_SCHEMA_VERSION=window.DotKeibaSaveCompat.SCHEMA_VERSION;
let activeSaveSlot=Math.max(1,Math.min(3,Number(localStorage.getItem(ACTIVE_SLOT_KEY))||1));
const saveSlotKey=slot=>`${SAVE_KEY_PREFIX}${slot}`;
window.DotKeibaSaveCompat.copyLegacySave(localStorage,LEGACY_SAVE_KEY,SAVE_KEY_PREFIX,3);
// 2歳から9歳末までの8年間。旧実装の240週（5年）固定により、
// 5年目12月以降に番組が消える不具合を防ぐ。
const CAREER_MAX_WEEKS = 384;
const screens = [...document.querySelectorAll(".game-screen")];
const coats = [["栗毛","#b96e32"],["鹿毛","#74401f"],["黒鹿毛","#3c2a25"],["芦毛","#b9b7ad"]];
const sires = [
  ["ドットキング","GⅡ 1勝","芝1800〜2400m","普通"],["レトロボルト","3勝クラス","ダート1400〜1800m","晩成"],["ピクセルロード","オープン","芝1200〜1600m","早熟"],
  ["エイトスター","2勝クラス","芝2200〜3000m","晩成"],["ファミコンテ","未勝利","ダート1000〜1400m","早熟"]
];
const dams = [
  ["メモリーハート","1勝クラス","芝1600〜2000m","普通"],["グリーンライン","未勝利","ダート1600〜1800m","晩成"],["チップクイーン","2勝クラス","芝1400〜1800m","早熟"],
  ["ブラウンベル","未出走","距離適性不明","普通"],["ドットミスト","1勝クラス","ダート1200〜1600m","晩成"]
];
const breedingPartners={
  "牡馬":[
    {name:"ゼロスタリオン",cost:0,record:"未勝利",surface:"芝・ダート不明",distance:"1200〜2000m",growth:"普通",level:430},
    {name:"ノーマネーボルト",cost:0,record:"未出走",surface:"ダート向き",distance:"1000〜1800m",growth:"早熟",level:420},
    {name:"フリーチップ",cost:0,record:"未勝利",surface:"芝向き",distance:"1400〜2200m",growth:"晩成",level:435},
    {name:"ハジマリロード",cost:0,record:"未勝利",surface:"芝・ダート不明",distance:"1200〜2400m",growth:"普通",level:425},
    {name:"ローカルエース",cost:500,record:"1勝クラス",surface:"ダート向き",distance:"1200〜1800m",growth:"早熟",level:500},
    {name:"ミドルダッシュ",cost:500,record:"1勝クラス",surface:"芝向き",distance:"1000〜1600m",growth:"早熟",level:505},
    {name:"ブラウンギア",cost:500,record:"1勝クラス",surface:"ダート向き",distance:"1600〜2200m",growth:"普通",level:495},
    {name:"スロースター",cost:500,record:"1勝クラス",surface:"芝向き",distance:"1800〜2600m",growth:"晩成",level:510},
    {name:"ターフメモリー",cost:1500,record:"3勝クラス",surface:"芝向き",distance:"1600〜2200m",growth:"普通",level:570},
    {name:"ダートブレイヴ",cost:1500,record:"3勝クラス",surface:"ダート向き",distance:"1400〜2000m",growth:"普通",level:575},
    {name:"スプリントキー",cost:1500,record:"2勝クラス",surface:"芝向き",distance:"1000〜1600m",growth:"早熟",level:565},
    {name:"ロングパス",cost:1500,record:"3勝クラス",surface:"芝向き",distance:"2000〜3000m",growth:"晩成",level:580},
    {name:"グランドチップ",cost:5000,record:"オープン",surface:"芝向き",distance:"1800〜2600m",growth:"晩成",level:650},
    {name:"サンドコマンド",cost:5000,record:"オープン",surface:"ダート向き",distance:"1200〜2000m",growth:"普通",level:645},
    {name:"マイルピクセル",cost:5000,record:"重賞 1勝",surface:"芝向き",distance:"1400〜1800m",growth:"早熟",level:655},
    {name:"ステイヤードット",cost:5000,record:"オープン",surface:"芝向き",distance:"2200〜3200m",growth:"晩成",level:660},
    {name:"レジェンドドット",cost:15000,record:"GⅠ 2勝",surface:"芝・万能",distance:"1600〜3000m",growth:"普通",level:735}
    ,{name:"キングオブチップ",cost:15000,record:"GⅠ 1勝",surface:"芝向き",distance:"1200〜2000m",growth:"早熟",level:725}
    ,{name:"ダートエンペラー",cost:15000,record:"GⅠ 2勝",surface:"ダート向き",distance:"1400〜2400m",growth:"晩成",level:730}
    ,{name:"エターナルビット",cost:15000,record:"GⅠ 1勝",surface:"芝向き",distance:"2000〜3200m",growth:"晩成",level:740}
  ],
  "牝馬":[
    {name:"ゼロメア",cost:0,record:"未出走",surface:"芝・ダート不明",distance:"1200〜2000m",growth:"普通",level:425},
    {name:"フリーベル",cost:0,record:"未勝利",surface:"芝向き",distance:"1200〜1800m",growth:"早熟",level:430},
    {name:"ノーコストラブ",cost:0,record:"未出走",surface:"ダート向き",distance:"1400〜2200m",growth:"普通",level:420},
    {name:"ハジマリメモリ",cost:0,record:"未勝利",surface:"芝・ダート不明",distance:"1600〜2400m",growth:"晩成",level:435},
    {name:"ローカルベル",cost:500,record:"1勝クラス",surface:"ダート向き",distance:"1400〜1800m",growth:"晩成",level:495},
    {name:"ターフスイート",cost:500,record:"1勝クラス",surface:"芝向き",distance:"1200〜1800m",growth:"早熟",level:500},
    {name:"サンドリボン",cost:500,record:"1勝クラス",surface:"ダート向き",distance:"1600〜2200m",growth:"普通",level:505},
    {name:"ロングメロディ",cost:500,record:"1勝クラス",surface:"芝向き",distance:"1800〜2600m",growth:"晩成",level:510},
    {name:"ターフリボン",cost:1500,record:"2勝クラス",surface:"芝向き",distance:"1400〜2200m",growth:"早熟",level:560},
    {name:"ダートパール",cost:1500,record:"3勝クラス",surface:"ダート向き",distance:"1200〜1800m",growth:"普通",level:570},
    {name:"ミドルハート",cost:1500,record:"3勝クラス",surface:"芝向き",distance:"1600〜2400m",growth:"普通",level:575},
    {name:"ステイヤーミスト",cost:1500,record:"2勝クラス",surface:"芝向き",distance:"2000〜3000m",growth:"晩成",level:580},
    {name:"クイーンメモリ",cost:5000,record:"オープン",surface:"芝向き",distance:"1600〜2400m",growth:"普通",level:640},
    {name:"サンドクイーン",cost:5000,record:"重賞 1勝",surface:"ダート向き",distance:"1400〜2000m",growth:"普通",level:650},
    {name:"スプリントベル",cost:5000,record:"オープン",surface:"芝向き",distance:"1000〜1600m",growth:"早熟",level:645},
    {name:"ロングティアラ",cost:5000,record:"オープン",surface:"芝向き",distance:"2000〜3000m",growth:"晩成",level:655},
    {name:"ダービーハート",cost:15000,record:"GⅠ 1勝",surface:"芝・万能",distance:"1600〜2800m",growth:"晩成",level:725}
    ,{name:"グランプリローズ",cost:15000,record:"GⅠ 2勝",surface:"芝向き",distance:"1800〜2600m",growth:"普通",level:735}
    ,{name:"ダートヴィーナス",cost:15000,record:"GⅠ 1勝",surface:"ダート向き",distance:"1200〜2200m",growth:"早熟",level:730}
    ,{name:"エンドレスメア",cost:15000,record:"GⅠ 1勝",surface:"芝向き",distance:"2200〜3200m",growth:"晩成",level:740}
  ]
};
let currentBreedingChoices=[];
const defaultGame = () => ({
  saveVersion:SAVE_SCHEMA_VERSION,
  horseName:"", week:1, trainingsUsed:0, prize:0, farmPoints:0, equipment:[], classMoney:0, priorityRights:[],
  speed:0, dash:0, gateSkill:450, stamina:0, power:0, guts:0, turf:0, dirt:0, heavyTrack:500, condition:60, fatigue:10,
  conditionDirection:1, conditionPhaseWeeks:4, conditionStability:"普通", conditionPeakWeeks:0,
  weight:0, baseBestWeight:0, growthType:"普通", growthPotential:12,
  generation:1, potentialCaps:null, ageDecline:0, distanceMin:1400, distanceMax:2000,
  injury:null, legCondition:100, recoveryPower:550, turnaroundTolerance:500,
  lastRaceWeek:null, raceLoad:0,
  temperament:"普通",temperamentValue:50,temperamentKnown:false,
  tackUnlocked:[],equippedTack:null,temperamentObservations:0,
  races:0, wins:0, maiden:true, selectedRace:null, currentRaceWeather:null,
  raceHistory:[], favoriteRaces:[], galleryUnlocks:["stable"], gradedTrophies:[], candidate:null,
  reservedRaceId:null,reservationNotifiedId:null,pendingOverseasOfferId:null,declinedOverseasInvites:[], affection:0, lineage:[],retirementRecords:[],equipmentDurability:{},equipmentAge:{},inheritanceComment:"",lastRaceAdvice:""
});
let game = defaultGame();
let autoTrainingActive=false;
let trainingAnimationActive=false;
let pendingRaceAfterSpacingWarning=null;
let developerMode=localStorage.getItem("dotKeibaDeveloperMode")==="1";
const ABILITY_STATS=["speed","dash","stamina","power","guts","turf","dirt","heavyTrack"];

const raceCalendar = [
  {id:"n1",week:21,name:"2歳新馬",raceClass:"新馬",course:"東京 芝1400m",surface:"芝",distance:1400,baseTime:83100,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n2",week:21,name:"2歳新馬",raceClass:"新馬",course:"東京 芝1600m",surface:"芝",distance:1600,baseTime:95800,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n3",week:21,name:"2歳新馬",raceClass:"新馬",course:"阪神 ダート1400m",surface:"ダート",distance:1400,baseTime:87600,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n4",week:22,name:"2歳新馬",raceClass:"新馬",course:"東京 芝1800m",surface:"芝",distance:1800,baseTime:108500,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n5",week:22,name:"2歳新馬",raceClass:"新馬",course:"阪神 ダート1800m",surface:"ダート",distance:1800,baseTime:115000,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"m1",week:22,name:"2歳未勝利",raceClass:"未勝利",course:"東京 芝1400m",surface:"芝",distance:1400,baseTime:82700,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m2",week:22,name:"2歳未勝利",raceClass:"未勝利",course:"阪神 ダート1400m",surface:"ダート",distance:1400,baseTime:87000,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m3",week:23,name:"2歳未勝利",raceClass:"未勝利",course:"東京 芝1600m",surface:"芝",distance:1600,baseTime:95100,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m4",week:23,name:"2歳未勝利",raceClass:"未勝利",course:"阪神 芝1800m",surface:"芝",distance:1800,baseTime:107800,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m5",week:24,name:"2歳未勝利",raceClass:"未勝利",course:"東京 ダート1600m",surface:"ダート",distance:1600,baseTime:98700,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"o0a",week:22,name:"2歳1勝クラス",raceClass:"1勝",course:"東京 芝1600m",surface:"芝",distance:1600,baseTime:93500,prize:800,difficulty:69,condition:g=>!g.maiden},
  {id:"o0b",week:22,name:"2歳1勝クラス",raceClass:"1勝",course:"阪神 ダート1400m",surface:"ダート",distance:1400,baseTime:85500,prize:800,difficulty:69,condition:g=>!g.maiden},
  {id:"o0c",week:23,name:"2歳1勝クラス",raceClass:"1勝",course:"東京 芝1800m",surface:"芝",distance:1800,baseTime:106900,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o0d",week:24,name:"2歳1勝クラス",raceClass:"1勝",course:"阪神 ダート1800m",surface:"ダート",distance:1800,baseTime:112500,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o0e",week:25,name:"2歳1勝クラス",raceClass:"1勝",course:"福島 芝1800m",surface:"芝",distance:1800,baseTime:108800,prize:800,difficulty:71,condition:g=>!g.maiden},
  {id:"o1",week:26,name:"2歳1勝クラス",raceClass:"1勝",course:"小倉 芝1200m",surface:"芝",distance:1200,baseTime:70800,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o2",week:27,name:"2歳1勝クラス",raceClass:"1勝",course:"新潟 ダート1200m",surface:"ダート",distance:1200,baseTime:73000,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o3",week:40,name:"百日草特別 1勝",raceClass:"1勝",course:"東京 芝2000m",surface:"芝",distance:2000,baseTime:121300,prize:1070,difficulty:71,condition:g=>!g.maiden},
  {id:"g3",week:43,name:"東京スポーツ杯2歳S GⅢ",raceClass:"G3",course:"東京 芝1800m",surface:"芝",distance:1800,baseTime:106500,prize:3300,difficulty:86,condition:g=>!g.maiden&&g.prize>=500},
  {id:"aoba",week:65,name:"青葉賞 GⅡ",raceClass:"G2",course:"東京 芝2400m",surface:"芝",distance:2400,baseTime:145000,prize:5400,difficulty:90,trialRight:{name:"日本ダービー",maxPlace:2},condition:g=>g.classMoney>=400},
  {id:"principal",week:66,name:"プリンシパルS L",raceClass:"オープン",course:"東京 芝2000m",surface:"芝",distance:2000,baseTime:120000,prize:2000,difficulty:84,trialRight:{name:"日本ダービー",maxPlace:1},condition:g=>g.classMoney>=400},
  {id:"derby",week:68,name:"日本ダービー GⅠ",raceClass:"G1",course:"東京 芝2400m",surface:"芝",distance:2400,baseTime:143500,prize:30000,difficulty:96,condition:g=>g.priorityRights.includes("日本ダービー")||g.classMoney>=1600},
];

// 2026年のJRA開催日割をゲーム内の月4週へ対応させた開催場テーブル。
// 新馬は初出走のみ。未出走馬を含む未勝利馬は未勝利戦へ出走できる。
const JRA_2026_VENUES=[
  [["中山","京都"],["中山","京都"],["中山","京都"],["東京","京都","小倉"]],
  [["東京","京都","小倉"],["東京","京都","小倉"],["東京","京都","小倉"],["中山","阪神","小倉"]],
  [["中山","阪神","小倉"],["中山","阪神","中京"],["中山","阪神","中京"],["中山","阪神","中京"]],
  [["中山","阪神","福島"],["中山","阪神","福島"],["東京","京都","福島"],["東京","京都","新潟"]],
  [["東京","京都","新潟"],["東京","京都","新潟"],["東京","京都","新潟"],["東京","京都"]],
  [["東京","阪神"],["東京","阪神","函館"],["東京","阪神","函館"],["福島","小倉","函館"]],
  [["福島","小倉","函館"],["福島","小倉","函館"],["福島","小倉","札幌"],["新潟","中京","札幌"]],
  [["新潟","中京","札幌"],["新潟","中京","札幌"],["新潟","中京","札幌"],["新潟","中京","札幌"]],
  [["中山","阪神","札幌"],["中山","阪神"],["中山","阪神"],["中山","阪神"]],
  [["東京","京都"],["東京","京都"],["東京","京都","新潟"],["東京","京都","新潟"]],
  [["東京","京都","福島"],["東京","京都","福島"],["東京","京都","福島"],["東京","京都","福島"]],
  [["中山","阪神","中京"],["中山","阪神","中京"],["中山","阪神","中京"],["中山","阪神"]]
];
const JRA_COURSE_DISTANCES={
  "札幌":{芝:[1000,1200,1500,1800,2000,2600],ダート:[1000,1700,2400]},
  "函館":{芝:[1000,1200,1700,1800,2000,2600],ダート:[1000,1700,2400]},
  "福島":{芝:[1000,1200,1700,1800,2000,2600],ダート:[1000,1150,1700,2400]},
  "新潟":{芝:[1000,1200,1400,1600,1800,2000,2200,2400,3000,3200],ダート:[1000,1200,1700,1800,2500]},
  "東京":{芝:[1400,1600,1800,2000,2300,2400,2500,2600,3400],ダート:[1200,1300,1400,1600,2100,2400]},
  "中山":{芝:[1200,1600,1800,2000,2200,2500,2600,3200,3600,4000],ダート:[1000,1200,1700,1800,2400,2500]},
  "中京":{芝:[1200,1300,1400,1600,2000,2200,3000],ダート:[1200,1400,1800,1900,2500]},
  "京都":{芝:[1100,1200,1400,1600,1800,2000,2200,2400,3000,3200],ダート:[1000,1100,1200,1400,1800,1900,2600]},
  "阪神":{芝:[1200,1400,1600,1800,2000,2200,2400,2600,3000,3200],ダート:[1200,1400,1800,2000,2600]},
  "小倉":{芝:[1000,1200,1700,1800,2000,2600],ダート:[1000,1700,2400]}
};
function venueRaceDistance(venue,surface,requested,week){
  const distances=JRA_COURSE_DISTANCES[venue]?.[surface]||[requested];
  if(requested==="long"){
    const long=distances.filter(distance=>distance>=2400);
    return long.length?long[(week+venue.length)%long.length]:distances.at(-1);
  }
  return distances.reduce((best,distance)=>Math.abs(distance-requested)<Math.abs(best-requested)?distance:best,distances[0]);
}
const PROGRAM_RACES=[
  [1,"未勝利","未勝利","ダート",1200,560,64],
  [2,"未勝利","未勝利","芝",1400,560,64],
  [3,"未勝利","未勝利","ダート",1400,560,64],
  [4,"未勝利","未勝利","芝",1600,560,64],
  [5,"新馬","新馬","芝",1600,750,63],
  [6,"新馬","新馬","ダート",1800,750,63],
  [7,"1勝クラス","1勝","芝",1400,800,69],
  [8,"1勝クラス","1勝","ダート",1400,800,69],
  [9,"1勝クラス","1勝","mixed","long",800,72],
  [10,"2勝クラス","2勝","mixed",2000,1140,76],
  [11,"3勝クラス特別","3勝","mixed","long",1840,82],
  [12,"オープン特別","オープン","mixed",1800,2200,85],
];
// 一般戦は同じ週の全会場が同じ馬場に偏らないよう、クラス別の比率と距離帯から決定する。
// 長距離は選択肢として残しつつ、短距離・マイル・中距離より低い頻度にしている。
const CLASS_PROGRAM_PROFILES={
  "1勝":{
    surfaces:["芝","ダート","芝","ダート","芝","ダート"],
    芝:[1200,1400,1600,1800,2000,2400],
    ダート:[1200,1400,1700,1800,2100]
  },
  "2勝":{
    surfaces:["芝","ダート","芝","ダート","芝","ダート"],
    芝:[1200,1400,1600,1800,2000,2200,2400],
    ダート:[1200,1400,1700,1800,1900,2100]
  },
  "3勝":{
    surfaces:["芝","ダート","芝","芝","ダート","芝"],
    芝:[1200,1400,1600,1800,2000,2200,2400,3000],
    ダート:[1200,1400,1700,1800,1900,2100]
  },
  "オープン":{
    surfaces:["芝","ダート","芝","芝","ダート","芝"],
    芝:[1200,1400,1600,1800,2000,2200,2400,3000],
    ダート:[1200,1400,1600,1700,1800,1900,2100]
  }
};
function programRotationIndex(week,venue,number,salt=0){
  const text=`${week}|${venue}|${number}|${salt}`;
  let hash=2166136261;
  for(let i=0;i<text.length;i++){hash^=text.charCodeAt(i);hash=Math.imul(hash,16777619)}
  return hash>>>0;
}
function classProgramSpec(raceClass,venue,week,number){
  const profile=CLASS_PROGRAM_PROFILES[raceClass];
  if(!profile)return null;
  const surface=profile.surfaces[programRotationIndex(week,venue,number)%profile.surfaces.length];
  const distances=profile[surface];
  const requestedDistance=distances[programRotationIndex(week,venue,number,7)%distances.length];
  return {surface,requestedDistance};
}
function classMoneyEligible(raceClass,g){
  if(raceClass==="1勝")return !g.maiden&&g.classMoney<=500;
  if(raceClass==="2勝")return !g.maiden&&g.classMoney>=501&&g.classMoney<=1000;
  if(raceClass==="3勝")return !g.maiden&&g.classMoney>=1001&&g.classMoney<=1600;
  if(raceClass==="オープン")return !g.maiden&&g.classMoney>1600;
  return false;
}
function generatedRaceCondition(raceClass,week,g){
  const age=2+Math.floor((week-1)/48),yearWeek=(week-1)%48;
  if(raceClass==="新馬")return age<=3&&!(age===3&&yearWeek>12)&&g.races===0;
  if(raceClass==="未勝利")return age<=3&&!(age===3&&yearWeek>36)&&g.maiden;
  return classMoneyEligible(raceClass,g);
}
function horseAgeAtWeek(week){return Math.min(9,2+Math.floor((week-1)/48))}
function programAgeLabel(week){
  const age=2+Math.floor((week-1)/48),yearWeek=(week-1)%48;
  if(age===2)return "2歳";
  if(age===3&&yearWeek<21)return "3歳";
  if(age===3)return "3歳以上";
  return yearWeek<21?"4歳以上":"3歳以上";
}
for(let week=1;week<=CAREER_MAX_WEEKS;week++){
  const calendarAge=horseAgeAtWeek(week),yearWeek=(week-1)%48,ageLimitedSeason=calendarAge===2||(calendarAge===3&&yearWeek<21),venues=JRA_2026_VENUES[Math.floor(yearWeek/4)][yearWeek%4];
  venues.forEach(venue=>PROGRAM_RACES.forEach(([number,baseName,baseClass,baseSurface,requestedDistance,prize,difficulty])=>{
    // 条件戦はクラス・開催場・週ごとのプロファイルで馬場と距離を分散する。
    let surface=baseSurface==="mixed"?((week+number)%2===0?"芝":"ダート"):baseSurface;
    let raceClass=baseClass,name=baseName,raceDistanceRequest=requestedDistance;
    const newRaceClosed=calendarAge>3||(calendarAge===3&&yearWeek>12);
    const maidenClosed=calendarAge>3||(calendarAge===3&&yearWeek>36);
    if((raceClass==="新馬"&&newRaceClosed)||(raceClass==="未勝利"&&maidenClosed)){
      raceClass=calendarAge>=4&&number>=4?number===6?"3勝":"2勝":"1勝";
      name=`${raceClass}クラス`;
    }else if(raceClass==="新馬"||raceClass==="未勝利")name=`${calendarAge}歳${raceClass}`;
    else if(raceClass==="1勝"&&number!==9)name=`${programAgeLabel(week)}1勝クラス`;
    if(number===9&&calendarAge===2){name="2歳1勝クラス";raceDistanceRequest=1800}
    const classSpec=classProgramSpec(raceClass,venue,week,number);
    if(classSpec){surface=classSpec.surface;raceDistanceRequest=classSpec.requestedDistance}
    if(number===9&&calendarAge===2)raceDistanceRequest=1800;
    if(raceDistanceRequest==="long"&&surface==="ダート")raceDistanceRequest=1800;
    if(number>=10&&ageLimitedSeason){raceClass="オープン";name=`${calendarAge}歳オープン`}
    const niigataStraight=venue==="新潟"&&surface==="芝"&&number===7;
    const distance=niigataStraight?1000:venueRaceDistance(venue,surface,raceDistanceRequest,week);
    const raceName=niigataStraight?`${programAgeLabel(week)}直線1000m 1勝クラス`:name;
    const basePer1000=niigataStraight?57000:surface==="芝"?60000:63000;
    raceCalendar.push({id:`p-${week}-${venue}-${number}`,program:true,number,week,name:raceName,raceClass,
      course:`${venue} ${surface}${distance}m`,surface,distance,
      baseTime:Math.round(basePer1000*distance/1000),prize,difficulty,
      age:raceClass==="新馬"||raceClass==="未勝利"?`${calendarAge}歳`:programAgeLabel(week),
      condition:g=>ageLimitedSeason&&raceClass==="オープン"?!g.maiden&&g.classMoney>=400:generatedRaceCondition(raceClass,week,g)});
  }));
}
const OFFICIAL_GRADE_LABEL={G1:"GⅠ",G2:"GⅡ",G3:"GⅢ",Jpn1:"JpnⅠ",Jpn2:"JpnⅡ",Jpn3:"JpnⅢ"};
const OFFICIAL_PRIZE={G1:12000,G2:6700,G3:4100,Jpn1:8000,Jpn2:4000,Jpn3:2500};
const OFFICIAL_DIFFICULTY={G1:96,G2:91,G3:86,Jpn1:95,Jpn2:90,Jpn3:85};
function officialWeek(date,year){
  const [,month,day]=date.split("-").map(Number),days=new Date(2026,month,0).getDate();
  return (year-1)*48+(month-1)*4+Math.min(4,Math.max(1,Math.ceil(day/days*4)));
}
function raceAgeTextEligible(text,age){
  if(text.includes("2歳")&&age!==2)return false;
  if(text.includes("3歳")&&!text.includes("以上")&&age!==3)return false;
  if(text.includes("4歳以上")&&age<4)return false;
  if(text.includes("3歳以上")&&age<3)return false;
  return true;
}
function officialRaceAgeEligible(race,g,raceWeek=game.week){
  const text=race.age||"";
  if(!raceAgeTextEligible(text,horseAgeAtWeek(raceWeek)))return false;
  if(text.includes("牝")&&g.candidate?.sex!=="牝馬")return false;
  return true;
}
function narAgeText(name){
  const female=/クイーン賞|兵庫女王|エンプレス|関東オークス|スパーキングレディー|ブリーダーズゴールド|マリーンカップ|レディスプレリュード|エーデルワイス|JBCレディス/.test(name);
  if(/2歳|エーデルワイス|兵庫ジュニア|全日本2歳/.test(name))return female?"2歳牝":"2歳";
  if(/ブルーバード|雲取|京浜盃|羽田盃|東京ダービー|兵庫チャンピオン|関東オークス|不来方|マリーンカップ|ジャパンダートクラシック|北海道スプリント/.test(name))return female?"3歳牝":"3歳";
  return female?"3歳以上牝":"3歳以上";
}
function addOfficialRaces(source,prefix){
  for(let year=1;year<=CAREER_MAX_WEEKS/48;year++)source.forEach((raw,index)=>{
    const official={...raw,age:raw.age||narAgeText(raw.name)};
    const raceWeek=officialWeek(raw.date,year);
    const normalizedClass=raw.grade.endsWith("1")?"G1":raw.grade.endsWith("2")?"G2":"G3";
    // 2・3歳限定重賞は勝ち上がり馬に門戸を残す。古馬重賞はオープン馬だけを対象にする。
    const ageLimitedGraded=/^(2歳|3歳)(?!以上)/.test(official.age);
    const classThreshold=ageLimitedGraded?(normalizedClass==="G1"?1601:1001):1601;
    raceCalendar.push({id:`${prefix}-${year}-${index}`,program:true,official:true,officialDate:raw.date,number:11,
      week:raceWeek,name:`${raw.name} ${OFFICIAL_GRADE_LABEL[raw.grade]}`,raceClass:normalizedClass,
      course:`${raw.venue} ${raw.surface}${raw.distance}m`,surface:raw.surface,distance:raw.distance,
      baseTime:Math.round((raw.surface==="芝"?60000:63000)*raw.distance/1000),prize:OFFICIAL_PRIZE[raw.grade],difficulty:OFFICIAL_DIFFICULTY[raw.grade],
      age:official.age,condition:g=>officialRaceAgeEligible(official,g,raceWeek)&&!g.maiden&&g.classMoney>=classThreshold});
  });
}
// 手作業の仮重賞は公式2026日程へ置き換える。
for(let i=raceCalendar.length-1;i>=0;i--)if(!raceCalendar[i].program&&["G1","G2","G3"].includes(raceCalendar[i].raceClass))raceCalendar.splice(i,1);
addOfficialRaces(window.OFFICIAL_JRA_GRADED_2026||[],"jra26");
addOfficialRaces(window.OFFICIAL_NAR_GRADED_2026||[],"nar26");
const OVERSEAS_G1=[
  {key:"dubai-world-cup",offset:12,name:"ドバイワールドカップ GⅠ",venue:"メイダン",surface:"ダート",distance:2000,baseTime:121000,prize:90000},
  {key:"king-george",offset:30,name:"キングジョージⅥ世＆クイーンエリザベスS GⅠ",venue:"アスコット",surface:"芝",distance:2400,baseTime:149000,prize:18000},
  {key:"arc",offset:37,name:"凱旋門賞 GⅠ",venue:"パリロンシャン",surface:"芝",distance:2400,baseTime:148000,prize:40000},
  {key:"bc-classic",offset:41,name:"ブリーダーズカップクラシック GⅠ",venue:"ブリーダーズカップ",surface:"ダート",distance:2000,baseTime:121000,prize:50000},
  {key:"hong-kong-sprint",offset:46,name:"香港スプリント GⅠ",venue:"シャティン",surface:"芝",distance:1200,baseTime:69000,prize:24000},
  {key:"hong-kong-mile",offset:46,name:"香港マイル GⅠ",venue:"シャティン",surface:"芝",distance:1600,baseTime:94300,prize:28000},
  {key:"hong-kong-cup",offset:46,name:"香港カップ GⅠ",venue:"シャティン",surface:"芝",distance:2000,baseTime:121000,prize:36000},
  {key:"hong-kong-vase",offset:46,name:"香港ヴァーズ GⅠ",venue:"シャティン",surface:"芝",distance:2400,baseTime:148500,prize:26000}
];
for(let year=1;year<=CAREER_MAX_WEEKS/48;year++)OVERSEAS_G1.forEach((race,index)=>raceCalendar.push({
  id:`overseas-${year}-${race.key}`,program:true,official:true,overseas:true,number:8+index%5,
  week:(year-1)*48+race.offset,name:race.name,raceClass:"G1",course:`${race.venue} ${race.surface}${race.distance}m`,
  surface:race.surface,distance:race.distance,baseTime:race.baseTime,prize:race.prize,difficulty:97,age:"3歳以上",
  condition:g=>!g.maiden&&g.classMoney>=2500&&(g.gradedTrophies||[]).some(t=>t.grade==="G1")
}));
// 公式重賞の開催場が月4週の簡易開催表から漏れた週も、1〜12Rの通常番組を補完する。
const centralJraVenues=new Set(["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"]);
const officialJraKeys=new Set(raceCalendar.filter(r=>r.official&&centralJraVenues.has(r.course.split(" ")[0])).map(r=>`${r.week}|${r.course.split(" ")[0]}`));
officialJraKeys.forEach(key=>{
  const [weekText,venue]=key.split("|"),week=Number(weekText);
  if(raceCalendar.some(r=>!r.official&&r.program&&r.week===week&&r.course.startsWith(`${venue} `)))return;
  const templateVenue=raceCalendar.find(r=>!r.official&&r.program&&r.week===week)?.course.split(" ")[0];
  const templates=raceCalendar.filter(r=>!r.official&&r.program&&r.week===week&&r.course.startsWith(`${templateVenue} `));
  templates.forEach(r=>{
    const distance=venueRaceDistance(venue,r.surface,r.distance,week);
    raceCalendar.push({...r,id:`supplement-${week}-${venue}-${r.number}`,course:`${venue} ${r.surface}${distance}m`,distance,
      baseTime:Math.round((r.surface==="芝"?60000:63000)*distance/1000)});
  });
});
// 月4週へ圧縮して同週・同場に重賞が複数ある場合は9〜11Rへ割り振り、仮番組と差し替える。
const officialRaceNumbers=new Map();
raceCalendar.filter(r=>r.official).forEach(r=>{
  const key=`${r.week}|${r.course.split(" ")[0]}`,group=officialRaceNumbers.get(key)||[];
  group.push(r);officialRaceNumbers.set(key,group);
});
officialRaceNumbers.forEach(group=>{
  const used=new Set(),key=`${group[0].week}|${group[0].course.split(" ")[0]}`;
  group.sort((a,b)=>String(a.officialDate||"").localeCompare(String(b.officialDate||""))).forEach(race=>{
    const candidates=[11,10,9,12];
    const sameSurface=candidates.find(number=>!used.has(number)&&raceCalendar.some(r=>!r.official&&r.program&&`${r.week}|${r.course.split(" ")[0]}`===key&&r.number===number&&r.surface===race.surface));
    race.number=sameSurface??candidates.find(number=>!used.has(number))??11;
    used.add(race.number);
  });
});
for(let i=raceCalendar.length-1;i>=0;i--){
  const race=raceCalendar[i];
  const officialNumbers=officialRaceNumbers.get(`${race.week}|${race.course.split(" ")[0]}`)?.map(r=>r.number)||[];
  if(!race.official&&race.program&&officialNumbers.includes(race.number))raceCalendar.splice(i,1);
}
const CLASS_TIME_ADJUST={
  "新馬":{芝:2.6,ダート:3.3},
  "未勝利":{芝:2.2,ダート:3.0},
  "1勝":{芝:1.6,ダート:2.4},
  "2勝":{芝:1.25,ダート:2.0},
  "3勝":{芝:.95,ダート:1.6},
  "オープン":{芝:.72,ダート:1.3},
  "G3":{芝:.55,ダート:1.05},
  "G2":{芝:.4,ダート:.85},
  "G1":{芝:.25,ダート:.65},
};
function raceAgeGroup(){return horseAge()===2?"2歳":"3歳以上"}
function raceVenue(race){return race.course.split(" ")[0]}
function raceTimingRecord(race){
  const master=window.RACE_TIME_MASTER;
  const venue=raceVenue(race),ageGroup=raceAgeGroup();
  const exactKey=`${venue}-${race.surface}-${race.distance}-${ageGroup}`;
  const openKey=`${venue}-${race.surface}-${race.distance}-3歳以上`;
  const exact=master?.records?.[exactKey]??master?.records?.[openKey];
  if(exact)return {time:exact,verified:true};
  const reference=master?.reference?.[`${race.surface}-${race.distance}`]??race.baseTime*.965;
  const venueData=master?.venues?.[venue]||master?.venues?.["東京"]||{turfFactor:1,dirtFactor:1};
  const factor=race.surface==="芝"?venueData.turfFactor:venueData.dirtFactor;
  return {time:Math.round(reference*factor),verified:false};
}
function officialRecordTime(race){return raceTimingRecord(race).time}
function classBenchmarkTime(race){
  const record=officialRecordTime(race);
  const secondsPerKm=CLASS_TIME_ADJUST[race.raceClass]?.[race.surface]??3;
  const twoYearOldExtra=horseAge()===2?race.raceClass==="新馬"?.9:race.raceClass==="未勝利"?.55:.2:0;
  return Math.round(record+(secondsPerKm+twoYearOldExtra)*race.distance);
}

function showScreen(id){ screens.forEach(s=>s.classList.toggle("active",s.id===id)); scrollTo(0,0); }
function saveGame(){ game.saveVersion=SAVE_SCHEMA_VERSION;localStorage.setItem(saveSlotKey(activeSaveSlot),JSON.stringify(game)); }
function loadGame(slot=activeSaveSlot){
  try{
    activeSaveSlot=slot;localStorage.setItem(ACTIVE_SLOT_KEY,String(slot));
    const key=saveSlotKey(slot),raw=localStorage.getItem(key);
    if(!raw)return false;
    const saved=JSON.parse(raw);
    const migration=window.DotKeibaSaveCompat.migrateSaveData(saved,defaultGame());
    // 初回移行時は元JSONを別キーへ残す。バックアップは上書きしない。
    if(migration.changed){
      const backupKey=`${key}BackupV${migration.fromVersion}`;
      if(!localStorage.getItem(backupKey))localStorage.setItem(backupKey,raw);
    }
    game=migration.data;
    if(!Number.isFinite(saved?.dash)||saved.dash<=0)game.dash=Math.max(400,Math.min(650,Math.round((game.speed+game.power)/2)-30));
    if(game.candidate&&!Number.isFinite(game.candidate.dash))game.candidate.dash=game.dash;
    if(!Number.isFinite(saved?.baseBestWeight)||saved.baseBestWeight<=0)game.baseBestWeight=rnd(438,492);
    if(!Number.isFinite(saved?.weight)||saved.weight<=0)game.weight=game.baseBestWeight+rnd(-4,6);
    if(!["早熟","普通","晩成"].includes(saved?.growthType))game.growthType="普通";
    if(!Number.isFinite(saved?.growthPotential))game.growthPotential=rnd(9,16);
    if(!saved?.potentialCaps)game.potentialCaps=createPotentialCaps(game);
    normalizePotentialCaps(game);
    if(!Number.isFinite(saved?.distanceMin))game.distanceMin=1400;
    if(!Number.isFinite(saved?.distanceMax))game.distanceMax=2000;
    if(!Number.isFinite(saved?.heavyTrack))game.heavyTrack=rnd(420,680);
    if(!Number.isFinite(saved?.recoveryPower))game.recoveryPower=rnd(430,670);
    if(!Number.isFinite(saved?.turnaroundTolerance))game.turnaroundTolerance=rnd(400,650);
    if(!Number.isFinite(saved?.lastRaceWeek))game.lastRaceWeek=null;
    if(!Number.isFinite(saved?.raceLoad))game.raceLoad=0;
    if(!Array.isArray(saved?.raceHistory))game.raceHistory=[];
    if(!Array.isArray(saved?.favoriteRaces))game.favoriteRaces=[];
    if(!Array.isArray(saved?.galleryUnlocks))game.galleryUnlocks=["stable"];
    if(!Array.isArray(saved?.gradedTrophies))game.gradedTrophies=(game.raceHistory||[]).filter(x=>x.place===1&&["G1","G2","G3"].includes(x.raceClass)).map(x=>({raceName:x.raceName,grade:x.raceClass,horseName:game.horseName,generation:game.generation,date:x.date}));
    if(!Array.isArray(saved?.declinedOverseasInvites))game.declinedOverseasInvites=[];
    if(!Number.isFinite(saved?.temperamentValue))game.temperamentValue=rnd(30,75);
    if(!saved?.temperament)game.temperament=temperamentType(game.temperamentValue);
    if(!Array.isArray(saved?.tackUnlocked))game.tackUnlocked=[];
    if(!game.equipmentDurability||typeof game.equipmentDurability!=="object")game.equipmentDurability={};
    if(!game.equipmentAge||typeof game.equipmentAge!=="object")game.equipmentAge={};
    game.equipment.forEach(id=>{if(!Number.isFinite(game.equipmentDurability[id]))game.equipmentDurability[id]=equipmentCatalog.find(x=>x.id===id)?.durability||80});
    game.equipment.forEach(id=>{if(!Number.isFinite(game.equipmentAge[id]))game.equipmentAge[id]=0});
    if(!Array.isArray(saved?.lineage))game.lineage=[];
    if(!Array.isArray(saved?.retirementRecords))game.retirementRecords=[];
    if(game.candidate&&!game.candidate.sex)game.candidate.sex="牡馬";
    if(!game.horseName)return false;
    if(migration.changed)saveGame();
    return true;
  }catch{return false}
}
function hasAnySave(){return [1,2,3].some(slot=>localStorage.getItem(saveSlotKey(slot)))}
function saveSlotSummary(slot){
  try{
    const saved=JSON.parse(localStorage.getItem(saveSlotKey(slot)));if(!saved?.horseName)return null;
    const week=Math.max(1,saved.week||1),year=Math.floor((week-1)/48)+1,month=Math.floor(((week-1)%48)/4)+1,weekOfMonth=(week-1)%4+1;
    return {horseName:saved.horseName,generation:saved.generation||1,date:`${year}年目 ${month}月${weekOfMonth}週`,record:`${saved.races||0}戦${saved.wins||0}勝`,prize:saved.prize||0};
  }catch{return null}
}
function renderSaveSlots(mode){
  document.querySelector("#saveSlotTitle").textContent=mode==="new"?"新しく始める枠":"つづきから遊ぶ枠";
  document.querySelector("#saveSlotList").dataset.mode=mode;
  document.querySelector("#saveSlotList").innerHTML=[1,2,3].map(slot=>{
    const data=saveSlotSummary(slot);
    return `<button class="save-slot-card ${data?"used":"empty"}" data-save-slot="${slot}"><b>セーブ ${slot}</b>${data?`<strong>${data.horseName}</strong><span>${data.generation}代目　${data.date}</span><small>${data.record}　${data.prize.toLocaleString()}万円</small>`:`<strong>あき</strong><span>新しい馬を育てられます</span>`}</button>`;
  }).join("");
}
function rnd(min,max){return Math.floor(Math.random()*(max-min+1))+min}
function temperamentType(value){
  return value>=74?"荒い":value>=60?"前向き":value>=42?"普通":value>=27?"臆病":"穏やか";
}
function inheritTemperament(sire,dam){
  const parentBias=(sire[3]==="早熟"?5:sire[3]==="晩成"?-2:0)+(dam[3]==="早熟"?3:dam[3]==="晩成"?-2:0);
  return Math.max(18,Math.min(88,rnd(32,70)+parentBias+rnd(-7,7)));
}
function inheritGrowthType(sireType,damType){
  const roll=Math.random();
  if(roll<.45)return sireType;
  if(roll<.80)return damType;
  return ["早熟","普通","晩成"][rnd(0,2)];
}
function parentDistanceRange(parent){
  const nums=(parent[2].match(/\d{4}/g)||[]).map(Number);
  return nums.length>=2?[nums[0],nums[1]]:[1200,2200];
}
function createDistanceRange(sire,dam){
  const sr=parentDistanceRange(sire),dr=parentDistanceRange(dam);
  const min=Math.round((sr[0]*.55+dr[0]*.45+rnd(-200,200))/200)*200;
  const max=Math.round((sr[1]*.55+dr[1]*.45+rnd(-200,200))/200)*200;
  return [Math.max(1000,Math.min(min,max-400)),Math.min(3200,Math.max(max,min+400))];
}
function createPotentialCaps(source){
  const caps={};
  ["speed","dash","stamina","power","guts","turf","dirt"].forEach(stat=>{
    const surface=stat==="turf"||stat==="dirt";
    const hardCap=surface?920:950;
    caps[stat]=Math.min(hardCap,source[stat]+rnd(surface?80:90,surface?190:220));
  });
  return caps;
}
function normalizePotentialCaps(source){
  if(!source.potentialCaps)source.potentialCaps=createPotentialCaps(source);
  ["speed","dash","stamina","power","guts","turf","dirt"].forEach(stat=>{
    const current=Number(source[stat])||0;
    const savedCap=Number(source.potentialCaps[stat]);
    source.potentialCaps[stat]=Math.max(current,Number.isFinite(savedCap)?savedCap:current);
  });
  return source.potentialCaps;
}
function inheritRecoveryTrait(parentValue,variation=80){
  return Math.max(300,Math.min(850,Math.round(parentValue*.55+rnd(400,700)*.45+rnd(-variation,variation))));
}
function generateCandidate(){
  const coat=Math.random()<.004?["白毛","#eee9dd"]:coats[rnd(0,coats.length-1)], sire=sires[rnd(0,sires.length-1)], dam=dams[rnd(0,dams.length-1)];
  const surfaceType=Math.random();
  const turf=surfaceType<.45?rnd(490,620):surfaceType<.9?rnd(350,475):rnd(470,590);
  const dirt=surfaceType<.45?rnd(350,475):surfaceType<.9?rnd(490,620):rnd(470,590);
  const baseBestWeight=rnd(438,492);
  const growthType=inheritGrowthType(sire[3],dam[3]);
  const temperamentValue=inheritTemperament(sire,dam);
  const [distanceMin,distanceMax]=createDistanceRange(sire,dam);
  const parentHeavyBase=(sire[2].includes("ダート")?5:0)+(dam[2].includes("ダート")?5:0);
  const candidate={coat:coat[0],color:coat[1],sex:Math.random()<.5?"牡馬":"牝馬",faceMark:Math.random()<.38,socks:rnd(0,4),eyeType:["優しい","鋭い","好奇心旺盛"][rnd(0,2)],sire,dam,speed:rnd(390,560),dash:rnd(370,540),gateSkill:rnd(380,540),stamina:rnd(390,560),power:rnd(380,550),guts:rnd(370,540),turf,dirt,heavyTrack:Math.max(350,Math.min(800,rnd(430,670)+parentHeavyBase*10)),temperamentValue,temperament:temperamentType(temperamentValue),baseBestWeight,weight:baseBestWeight+rnd(12,20),growthType,growthPotential:rnd(7,15),distanceMin,distanceMax,recoveryPower:rnd(380,760),turnaroundTolerance:rnd(340,740),...createConditionCycle()};
  candidate.potentialCaps=createPotentialCaps(candidate);
  game.candidate=candidate;
  document.querySelector("#candidateTitle").textContent=`${coat[0]}の2歳${candidate.sex}`;
  document.querySelector("#candidateHorse").style.setProperty("--horse-color",coat[1]);
  document.querySelector("#candidatePedigree").innerHTML=
    `父 ${sire[0]}（${sire[1]}）<br>得意 ${sire[2]}／成長型 ${sire[3]}<br>`+
    `母 ${dam[0]}（${dam[1]}）<br>得意 ${dam[2]}／成長型 ${dam[3]}`;
  document.querySelector("#candidateInfo").innerHTML=[
    ["スピード",game.candidate.speed],["ダッシュ",game.candidate.dash],["スタミナ",game.candidate.stamina],["パワー",game.candidate.power],
    ["勝負根性",game.candidate.guts],["馬体重",`${game.candidate.weight}kg`],["芝適性",turf],["ダート適性",dirt],["道悪適性",game.candidate.heavyTrack]
  ].map(([k,v])=>`<span>${k}<b>${typeof v==="number"?scoutComment(k,v):v}</b></span>`).join("");
}
function renderRetirement(){
  document.querySelector("#retirementHorseName").textContent=game.horseName;
  document.querySelector("#retirementSummary").textContent=`${game.generation}世代目　${game.races}戦${game.wins}勝　獲得賞金 ${game.prize.toLocaleString()}万円`;
  document.querySelector("#breedingBudget").textContent=`配合予算 ${game.prize.toLocaleString()}万円`;
  const partnerSex=game.candidate?.sex==="牝馬"?"牡馬":"牝馬";
  document.querySelector("#breedingGuide").textContent=`${game.candidate?.sex||"牡馬"}として引退します。相手となる${partnerSex}を選んでください。獲得賞金以内の相手を選べます。`;
  currentBreedingChoices=[...new Set(breedingPartners[partnerSex].map(partner=>partner.cost))].sort((a,b)=>a-b).map(cost=>{
    const tier=breedingPartners[partnerSex].filter(partner=>partner.cost===cost);
    return tier[rnd(0,tier.length-1)];
  });
  document.querySelector("#breedingPartners").innerHTML=currentBreedingChoices.map((partner,index)=>{
    const affordable=game.prize>=partner.cost;
    return `<article class="breeding-card ${affordable?"":"locked"}"><div><small>${partner.record}</small><h3>${partner.name}</h3><p>${partner.surface}／${partner.distance}／${partner.growth}</p></div><button data-breeding-partner="${index}" data-partner-sex="${partnerSex}" ${affordable?"":"disabled"}>${partner.cost.toLocaleString()}万円</button></article>`;
  }).join("");
}
function inheritedStat(parentValue,partnerLevel,variation=55){
  return Math.max(350,Math.min(760,Math.round(parentValue*.38+partnerLevel*.37+rnd(390,540)*.25+rnd(-variation,variation))));
}
function inheritanceComparison(child,parent){
  const labels={speed:"スピード",dash:"ダッシュ",stamina:"スタミナ",power:"パワー",guts:"勝負根性",turf:"芝適性",dirt:"ダート適性"};
  const differences=Object.keys(labels).map(stat=>({label:labels[stat],diff:(child.potentialCaps?.[stat]||child[stat])-(parent.potentialCaps?.[stat]||parent[stat])})).sort((a,b)=>b.diff-a.diff);
  const better=differences.find(x=>x.diff>=18),weaker=[...differences].reverse().find(x=>x.diff<=-18);
  const comments=[];
  if(better)comments.push(`${better.label}の素質は親より優れていそうです`);
  else comments.push("全体の素質は親とよく似ています");
  if(weaker)comments.push(`一方で${weaker.label}は、まだ親に及ばないかもしれません`);
  if(child.distanceMax>parent.distanceMax+200)comments.push("親より長い距離にも対応できる可能性があります");
  else if(child.distanceMax<parent.distanceMax-200)comments.push("距離は親より短めの方が合いそうです");
  if(child.growthType!==parent.growthType)comments.push(`成長の仕方は親の${parent.growthType}型とは違い、${child.growthType}型に出ています`);
  return comments.join("。")+"。これからの調教で見極めていきましょう。";
}
function beginNextGeneration(partner){
  const retired={name:game.horseName,sex:game.candidate?.sex||"牡馬",generation:game.generation,races:game.races,wins:game.wins,prize:game.prize,growthType:game.growthType,distanceMin:game.distanceMin,distanceMax:effectiveDistanceRange().max,coat:game.candidate?.coat||"栗毛",sire:game.candidate?.sire?.[0]||"不明",dam:game.candidate?.dam?.[0]||"不明"};
  const partnerTuple=[partner.name,partner.record,partner.distance,partner.growth];
  const currentTuple=[game.horseName,`${game.races}戦${game.wins}勝`,`${Math.round(game.distanceMin/100)*100}〜${Math.round(effectiveDistanceRange().max/100)*100}m`,game.growthType];
  const sire=retired.sex==="牡馬"?currentTuple:partnerTuple;
  const dam=retired.sex==="牝馬"?currentTuple:partnerTuple;
  const [distanceMin,distanceMax]=createDistanceRange(sire,dam);
  const coat=Math.random()<.004?["白毛","#eee9dd"]:(Math.random()<.58?[game.candidate?.coat||"栗毛",game.candidate?.color||"#b96e32"]:coats[rnd(0,coats.length-1)]);
  const level=partner.level;
  const child={
    coat:coat[0],color:coat[1],sex:Math.random()<.5?"牡馬":"牝馬",faceMark:Math.random()<(game.candidate?.faceMark ? .55 : .32),socks:rnd(0,4),eyeType:["優しい","鋭い","好奇心旺盛"][rnd(0,2)],sire,dam,
    speed:inheritedStat(game.speed,level),dash:inheritedStat(game.dash,level),gateSkill:inheritedStat(game.gateSkill,level,45),stamina:inheritedStat(game.stamina,level),power:inheritedStat(game.power,level),guts:inheritedStat(game.guts,level),
    turf:inheritedStat(game.turf,level,70),dirt:inheritedStat(game.dirt,level,70),heavyTrack:inheritedStat(game.heavyTrack,level,75),
    temperamentValue:Math.max(18,Math.min(88,Math.round(game.temperamentValue*.55+rnd(25,75)*.45))),baseBestWeight:Math.max(400,Math.min(540,Math.round(game.baseBestWeight*.55+rnd(430,500)*.45+rnd(-12,12)))),
    growthType:inheritGrowthType(game.growthType,partner.growth),growthPotential:Math.max(7,Math.min(20,Math.round(game.growthPotential*.45+(level-380)/35+rnd(-2,2)))),distanceMin,distanceMax,
    recoveryPower:inheritRecoveryTrait(game.recoveryPower),turnaroundTolerance:inheritRecoveryTrait(game.turnaroundTolerance),...createConditionCycle()
  };
  child.temperament=temperamentType(child.temperamentValue);
  child.weight=child.baseBestWeight+rnd(12,20);
  child.potentialCaps=createPotentialCaps(child);
  child.inheritanceComment=inheritanceComparison(child,{...game,potentialCaps:game.potentialCaps,distanceMax:effectiveDistanceRange().max});
  const legacy={generation:game.generation+1,farmPoints:game.farmPoints,equipment:[...game.equipment],equipmentDurability:{...game.equipmentDurability},equipmentAge:{...game.equipmentAge},galleryUnlocks:[...game.galleryUnlocks],gradedTrophies:[...(game.gradedTrophies||[])],favoriteRaces:[...game.favoriteRaces],lineage:[...game.lineage,retired],retirementRecords:[...game.retirementRecords,retired]};
  game={...defaultGame(),...legacy,candidate:child};
  document.querySelector("#candidateNumber").textContent=`${game.generation}世代目`;
  document.querySelector("#candidateTitle").textContent=`${child.coat}の2歳${child.sex}`;
  document.querySelector("#candidateHorse").style.setProperty("--horse-color",child.color);
  document.querySelector("#candidatePedigree").innerHTML=`父 ${sire[0]}（${sire[1]}）<br>得意 ${sire[2]}／成長型 ${sire[3]}<br>母 ${dam[0]}（${dam[1]}）<br>得意 ${dam[2]}／成長型 ${dam[3]}`;
  document.querySelector("#candidateInfo").innerHTML=[["スピード",child.speed],["ダッシュ",child.dash],["スタミナ",child.stamina],["パワー",child.power],["勝負根性",child.guts],["馬体重",`${child.weight}kg`],["芝適性",child.turf],["ダート適性",child.dirt],["道悪適性",child.heavyTrack]].map(([k,v])=>`<span>${k}<b>${typeof v==="number"?scoutComment(k,v):v}</b></span>`).join("");
  document.querySelector("#rerollHorseButton").hidden=true;
  document.querySelector("#horseNameInput").value="";
  document.querySelector("#birthHorse").style.setProperty("--horse-color",child.color);
  document.querySelector("#birthGeneration").textContent=`${game.generation}世代目 誕生`;
  document.querySelector("#birthMessage").textContent=`${child.coat}の${child.sex}が元気に産まれました。`;
  showScreen("birthScreen");
}
function gameYear(){return Math.floor((game.week-1)/48)+1}
function weekLabel(){const yearWeek=(game.week-1)%48,month=Math.floor(yearWeek/4)+1,w=yearWeek%4+1;return `${gameYear()}年目 ${month}月${w}週`;}
function horseAge(){return Math.min(9,2+Math.floor((game.week-1)/48));}
function maturityRate(){
  const age=horseAge()+((game.week-1)%48)/48;
  const curves={
    "早熟":[[2,.82],[3,.97],[4,1],[5,.98],[6,.94],[7,.88]],
    "普通":[[2,.70],[3,.86],[4,.97],[5,1],[6,.98],[7,.93]],
    "晩成":[[2,.58],[3,.72],[4,.87],[5,.97],[6,1],[7,.98]]
  };
  const points=curves[game.growthType]||curves["普通"];
  if(age<=points[0][0])return points[0][1];
  for(let i=1;i<points.length;i++){
    if(age<=points[i][0]){
      const [a0,r0]=points[i-1],[a1,r1]=points[i],t=(age-a0)/(a1-a0);
      return r0+(r1-r0)*t;
    }
  }
  return Math.max(.82,points.at(-1)[1]-(age-points.at(-1)[0])*.04);
}
function growthPeakAge(){
  return game.growthType==="早熟"?4:game.growthType==="晩成"?6:5;
}
function growthTrainingMultiplier(){
  const age=horseAge()+((game.week-1)%48)/48;
  if(game.growthType==="早熟")return age<3?1.18:age<4?1.08:age<5?.88:.55;
  if(game.growthType==="晩成")return age<3?.55:age<4?.72:age<5?.92:age<7?1.10:.82;
  return age<3?.78:age<4?.95:age<6?1.05:.72;
}
function effectivePotentialCap(stat){
  const base=game.potentialCaps?.[stat]??1000;
  return Math.max(300,base-(game.ageDecline||0));
}
function applyWeeklyPeakDecline(){
  const age=horseAge()+((game.week-1)%48)/48,yearsPast=age-growthPeakAge();
  if(yearsPast<=0)return;
  const weekly=(game.growthType==="早熟"?.22:game.growthType==="晩成"?.12:.17)*(1+Math.min(2,yearsPast)*.35);
  game.ageDecline=Math.min(180,(game.ageDecline||0)+weekly);
  ["speed","dash","stamina","power","guts"].forEach(stat=>{
    game[stat]=Math.max(300,Math.min(game[stat]-weekly,effectivePotentialCap(stat)));
  });
}
function growthAbilityBonus(){return game.growthPotential*10*(maturityRate()-.58)/.42;}
function effectiveDistanceRange(){
  // 血統由来の基礎距離を、現在のスタミナで長距離側へ拡張する。
  // スタミナ55を基準に、1ポイントごとに約20m対応距離が伸びる。
  const staminaExtension=Math.max(0,game.stamina-550)*2;
  return {
    min:game.distanceMin,
    max:Math.min(3400,Math.round(game.distanceMax+staminaExtension))
  };
}
function distanceAbilityPenalty(distance){
  const range=effectiveDistanceRange();
  const gap=distance<range.min?range.min-distance:distance>range.max?distance-range.max:0;
  if(gap<=0)return 0;
  // 200m程度なら相手や展開次第で対応可能。大きく外れると急激に厳しくなる。
  if(gap<=200)return gap/100*15;
  if(gap<=400)return 30+(gap-200)/100*20;
  if(gap<=800)return 70+(gap-400)/100*25;
  return Math.min(220,170+(gap-800)/100*12.5);
}
function trainingGain(stat,base,mult,type){
  const cap=effectivePotentialCap(stat);
  const remaining=Math.max(0,cap-game[stat]);
  if(remaining<=0||mult<=0)return 0;
  const capFactor=remaining>=120?1:remaining>=70?.72:remaining>=30?.45:.22;
  const equipmentBonus=
    stat==="power"&&type.startsWith("hill")&&game.equipment.includes("treadmill")?5:
    stat==="stamina"&&type==="pool"&&game.equipment.includes("waterWalker")?5:
    stat==="dash"&&type==="gate"&&game.equipment.includes("startingGate")?5:
    stat==="stamina"&&type.startsWith("dirt")&&game.equipment.includes("altitude")?3:0;
  const legFactor=game.legCondition>=80?1:game.legCondition>=60?.94:game.legCondition>=40?.84:.7;
  return Math.min(remaining,(base*6+equipmentBonus)*mult*growthTrainingMultiplier()*capFactor*legFactor);
}
function bestWeight(){
  const age=horseAge();
  // 成長分は2～4歳を中心に増加し、5歳末で頭打ち。
  const completedYears=Math.max(0,Math.min(4,age-2));
  const currentYearProgress=age<6?((game.week-1)%48)/48:0;
  const yearlyGrowth=[10,7,4,2];
  return Math.round(game.baseBestWeight+
    yearlyGrowth.slice(0,completedYears).reduce((a,b)=>a+b,0)+
    (age<6?(yearlyGrowth[completedYears]||0)*currentYearProgress:0));
}
function weightComment(){
  const diff=game.weight-bestWeight();
  if(diff>=18)return "かなり太目です";
  if(diff>=9)return "まだ太目です";
  if(diff<=-18)return "かなり細すぎます";
  if(diff<=-9)return "少し細い状態です";
  if(Math.abs(diff)<=3)return "ベスト体重です";
  return diff>0?"少し余裕があります":"少し絞れています";
}
function conditionLabel(){return game.condition>=85?"絶好調":game.condition>=68?"好調":game.condition>=45?"普通":game.condition>=28?"不調":"絶不調"}
function createConditionCycle(){
  const stability=["ムラ","普通","安定"][rnd(0,2)];
  return {
    condition:rnd(48,70),
    conditionDirection:Math.random()<.68?1:-1,
    conditionPhaseWeeks:stability==="ムラ"?rnd(2,4):stability==="安定"?rnd(5,8):rnd(3,6),
    conditionStability:stability,
    conditionPeakWeeks:0
  };
}
function conditionTrendComment(){
  if(game.condition>=85&&game.conditionPeakWeeks>0)return "今が一番良い時期でしょう。この状態でレースを迎えたいですね";
  if(game.conditionDirection>0)return game.condition>=75?"調子はかなり上向いてきました。ピークが近そうです":"徐々に調子が上向いてきました";
  if(game.conditionDirection<0)return game.condition<=38?"まだ本調子ではありません。立て直す時間が必要です":"少し調子が下降気味です。疲れを残さないようにしましょう";
  return game.condition>=78?"好調を維持しています":"調子は安定しています";
}
function advanceConditionCycle(actionBonus=0){
  let natural=0;
  if(game.conditionPeakWeeks>0){
    game.conditionPeakWeeks--;
    game.conditionDirection=0;
    natural=rnd(-1,1);
    if(game.conditionPeakWeeks===0){
      game.conditionDirection=-1;
      game.conditionPhaseWeeks=game.conditionStability==="安定"?rnd(5,8):game.conditionStability==="ムラ"?rnd(2,4):rnd(3,6);
    }
  }else{
    const range=game.conditionStability==="ムラ"?[4,8]:game.conditionStability==="安定"?[2,4]:[3,6];
    natural=rnd(range[0],range[1])*game.conditionDirection;
    game.conditionPhaseWeeks--;
    if(game.conditionDirection>0&&game.condition+natural>=86){
      game.conditionPeakWeeks=game.conditionStability==="安定"?rnd(2,4):rnd(1,2);
      game.conditionDirection=0;
    }else if(game.conditionPhaseWeeks<=0){
      game.conditionDirection*=-1;
      game.conditionPhaseWeeks=game.conditionStability==="安定"?rnd(5,8):game.conditionStability==="ムラ"?rnd(2,4):rnd(3,6);
    }
  }
  let nextCondition=game.condition+natural+actionBonus;
  if(game.conditionDirection<0&&nextCondition<=27){
    nextCondition=27;
    game.conditionDirection=1;
    game.conditionPhaseWeeks=game.conditionStability==="ムラ"?rnd(2,3):game.conditionStability==="安定"?rnd(4,6):rnd(3,4);
  }
  game.condition=Math.max(20,Math.min(100,nextCondition));
}
function classLabel(){
  if(game.maiden)return "未勝利";
  const age=horseAge(),yearWeek=(game.week-1)%48;
  if((age===2||(age===3&&yearWeek<21))&&game.classMoney>500)return "オープン";
  return game.classMoney<=500?"1勝クラス":game.classMoney<=1000?"2勝クラス":game.classMoney<=1600?"3勝クラス":"オープン";
}
function displayClassLabel(){return game.races===0?"新馬":classLabel()}
function classAbilityTarget(){
  const label=displayClassLabel();
  return label==="新馬"?500:label==="未勝利"?530:label==="1勝クラス"?610:label==="2勝クラス"?680:label==="3勝クラス"?750:820;
}
function legLabel(){return game.legCondition>=85?"良好":game.legCondition>=65?"少し張り":game.legCondition>=45?"注意":"危険"}
function legCoachComment(){
  if(game.injury)return `${game.injury.name}を発症しています。長期放牧が必要です`;
  if(game.legCondition>=85)return "すっきりしています。通常の調教を行えます";
  if(game.legCondition>=65)return "少し張りがあります。プールか軽め調整を挟むと安心です";
  if(game.legCondition>=45)return game.equipment.includes("hotSpring")?"張りが強く出ています。温泉療養を勧めます":"強い調教は避け、森林馬道・プール・休養で戻しましょう";
  return game.equipment.includes("hotSpring")?"故障寸前です。今週は温泉療養か放牧を選んでください":"故障寸前です。調教を中止し、放牧を強く勧めます";
}
function raceConditionModifier(){
  if(game.condition>=85)return 30;
  if(game.condition>=68)return 15;
  if(game.condition>=45)return 0;
  if(game.condition>=28)return -30;
  return -60;
}
function abilityBand(value){
  if(value>=900)return "規格外の可能性";
  if(value>=800)return "かなり高い水準";
  if(value>=700)return "水準以上";
  if(value>=600)return "まずまず";
  if(value>=500)return "標準的";
  if(value>=400)return "もう少し欲しい";
  return "まだ力不足";
}
function scoutComment(label,value){
  if(label.includes("芝")||label.includes("ダート"))return value>=700?"かなり向いていそう":value>=580?"適性がありそう":value>=460?"こなせそう":"少し不安があります";
  if(label==="道悪適性")return value>=700?"道悪は歓迎です":value>=520?"特に問題なさそう":"悪い馬場は気になります";
  return abilityBand(value);
}
function statRow(label,value,color){
  if(developerMode){
    const cap=game.potentialCaps?.[{スピード:"speed",ダッシュ:"dash",スタミナ:"stamina",パワー:"power",勝負根性:"guts",芝適性:"turf",ダート適性:"dirt",道悪適性:"heavyTrack"}[label]];
    return `<div class="dev-stat"><span>${label}</span><div class="meter"><i style="width:${value/10}%;background:${color}"></i></div><b>${Math.round(value)}${cap?`/${Math.round(cap)}`:""}</b></div>`;
  }
  return `<div class="trainer-stat"><span>${label}</span><b>${scoutComment(label,value)}</b></div>`;
}
const STAT_LABELS={speed:"スピード",dash:"ダッシュ",stamina:"スタミナ",power:"パワー",guts:"勝負根性",turf:"芝の走り",dirt:"ダートの走り"};
function trainingCoachComment(type,outcome,gains){
  if(outcome==="失敗")return "今日はうまく走りに集中できませんでした。疲れを取って立て直しましょう。";
  const improved=Object.entries(gains).filter(([,gain])=>gain>.1).sort((a,b)=>b[1]-a[1]);
  if(!improved.length)return "動きは悪くありませんが、能力は頭打ちに近いようです。別の調教も試しましょう。";
  const [mainStat,mainGain]=improved[0];
  const value=game[mainStat],cap=game.potentialCaps?.[mainStat]??1000;
  let growth;
  if(outcome==="大成功")growth=`${STAT_LABELS[mainStat]}が大きく良くなりました。今日の動きは素晴らしいです。`;
  else if(mainGain>=8)growth=`${STAT_LABELS[mainStat]}が目に見えて良くなってきました。`;
  else if(mainGain>=4)growth=`${STAT_LABELS[mainStat]}に少し成長が見られます。`;
  else growth=`${STAT_LABELS[mainStat]}はわずかに良くなりました。`;
  let advice;
  if(cap-value<35)advice="この部分はかなり完成に近づいています。";
  else if(value<470)advice=`ただ、${STAT_LABELS[mainStat]}はまだもう少し欲しいですね。`;
  else if(value<620)advice="このまま地道に積み重ねていきましょう。";
  else if(value<760)advice="水準以上の動きになってきました。";
  else advice="かなり高いレベルまで仕上がっています。";
  const secondary=improved[1]&&improved[1][1]>.1?` ${STAT_LABELS[improved[1][0]]}にも良い変化があります。`:"";
  return `${growth}${secondary} ${advice}`;
}
function nextTrainingAdvice(){
  if(game.fatigue>=65)return "今は能力を伸ばすより、休養で疲れを抜くことを優先しましょう。";
  const weightDiff=game.weight-bestWeight();
  if(weightDiff>=12)return "まだ太めです。坂路単走かダート単走で馬体を絞るのがよさそうです。";
  if(weightDiff<=-12)return "馬体が細いので、強い併せ馬は避けて休養を挟みましょう。";
  const targets=[
    ["speed","スピード","芝単走"],
    ["dash","ダッシュ","ゲート訓練か坂路併せ"],
    ["stamina","スタミナ","ダート単走"],
    ["power","パワー","坂路単走"],
    ["guts","勝負根性","芝・ダート・坂路の併せ馬"]
  ];
  const target=classAbilityTarget();
  const [stat,label,menu]=targets.sort((a,b)=>(game[a[0]]-target)-(game[b[0]]-target))[0];
  if(game[stat]<target-70)return `このクラスで戦うには${label}がまだ不足しています。${menu}を中心に鍛えましょう。`;
  if(game[stat]<target)return `このクラスで安定して走るには${label}がもう少し欲しいですね。${menu}で補強しましょう。`;
  const nextTarget=target+55;
  const [nextStat,nextLabel,nextMenu]=targets.sort((a,b)=>(game[a[0]]-nextTarget)-(game[b[0]]-nextTarget))[0];
  return `このクラスで戦う力は整いつつあります。次のクラスを考えるなら${nextLabel}を${nextMenu}で伸ばしたいですね。`;
}
function raceSuitabilityAdvice(race,place){
  if(!race)return "次走へ向けて、全体の底上げを続けましょう。";
  const range=effectiveDistanceRange();
  const hints=[];
  if(race.distance>range.max){
    hints.push("今回は距離が長かったようです。スタミナを鍛えれば、もう少し長い距離にも対応できそうです");
  }else if(race.distance<range.min){
    hints.push("今回は距離が短く、追走に忙しかったようです。ダッシュとスピードを伸ばしたいですね");
  }else if(race.distance>=range.max-200){
    hints.push("距離はこなせますが、終いに余裕を持たせるにはスタミナがもう少し欲しいです");
  }else if(race.distance<=range.min+200){
    hints.push("距離はこなせます。短い距離で安定させるならダッシュを磨きたいですね");
  }else{
    hints.push("距離は合っていそうです");
  }
  const used= race.surface==="芝"?game.turf:game.dirt;
  const other=race.surface==="芝"?game.dirt:game.turf;
  if(used+90<other)hints.push(`${race.surface}より${race.surface==="芝"?"ダート":"芝"}の方が向いている可能性があります`);
  else if(used<500)hints.push(`${race.surface}への適性はまだ心もとない印象です`);
  else hints.push(`${race.surface}はこなせそうです`);
  if(place>3){
    const basics=[[game.speed,"スピード"],[game.dash,"ダッシュ"],[game.stamina,"スタミナ"],[game.power,"パワー"],[game.guts,"勝負根性"]].sort((a,b)=>a[0]-b[0]);
    const shortage=basics[0][0]<classAbilityTarget()
      ? `${basics[0][1]}がまだ不足しています`
      : `${basics[0][1]}をもう少し伸ばしたいところです`;
    hints.push(`このクラスで戦うには${shortage}。ここを重点的に鍛えると、内容が変わってきそうです`);
  }
  return hints.join("。")+"。";
}
const tackCatalog={
  hood:{name:"メンコ",desc:"音への反応と出遅れを軽減"},
  blinkers:{name:"ブリンカー",desc:"前方へ集中。掛かりには注意"},
  cheekpieces:{name:"チークピーシズ",desc:"馬群での集中力を補助"}
};
function trainerTemperamentComment(){
  if(!game.temperamentKnown)return "まだ性格を見極めている段階です";
  if(game.temperament==="荒い")return "力みやすく、折り合いに注意が必要です";
  if(game.temperament==="前向き")return "前進気勢が強く、序盤に行きたがります";
  if(game.temperament==="臆病")return "周囲の音や他馬を気にするところがあります";
  if(game.temperament==="穏やか")return "落ち着いていますが、反応が鈍い時があります";
  return "気性は安定しています";
}
function fatigueCoachComment(){
  if(game.injury)return `${game.injury.name}を発症しています。今は調教せず、長期放牧で回復を待ちましょう。`;
  if(game.fatigue>=80)return "疲れが限界に近づいています。この状態で調教を続けると故障につながります。今週は休ませてください。";
  if(game.fatigue>=65)return "かなり疲れがたまっています。このまま強い調教を続けると故障するかもしれません。休養を考えましょう。";
  if(game.fatigue>=45)return "疲れがたまってきています。脚元への負担が大きい調教は、少し控えた方がよさそうです。";
  if(game.fatigue>=25)return "少し疲れが見えます。様子を見ながら調教を選びましょう。";
  return "元気があります。今週もしっかり動けそうです。";
}
function raceIntervalState(targetWeek=game.week){
  if(!Number.isFinite(game.lastRaceWeek))return {gap:null,label:"初出走",level:"none"};
  const gap=Math.max(0,targetWeek-game.lastRaceWeek);
  if(gap===1)return {gap,label:"連闘",level:"danger"};
  if(gap===2)return {gap,label:"中1週",level:"warning"};
  if(gap===3)return {gap,label:"中2週",level:"caution"};
  return {gap,label:`中${Math.max(0,gap-1)}週`,level:"safe"};
}
function recoveryTraitComment(){
  if(game.recoveryPower>=700)return "疲れの抜けがかなり早いタイプです";
  if(game.recoveryPower>=580)return "疲れは比較的抜けやすいタイプです";
  if(game.recoveryPower<420)return "疲れが残りやすいので、間隔を取った方がよさそうです";
  return "疲れの抜け方は標準的です";
}
function raceSpacingCoachWarning(targetWeek=game.week){
  const spacing=raceIntervalState(targetWeek);
  if(spacing.gap===null)return "";
  const tolerant=game.turnaroundTolerance>=650;
  if(spacing.gap===1){
    if(game.fatigue>=70||game.legCondition<55)return "連闘になります。疲れと脚元の張りが強く、故障の危険があります。今回は見送ることを強く勧めます";
    if(tolerant&&game.fatigue<48)return "連闘になります。この馬は詰めた間隔に対応できそうですが、普段より故障には注意が必要です";
    return "連闘になります。前走の疲れが残る可能性があり、能力低下と故障リスクを覚悟する必要があります";
  }
  if(spacing.gap===2){
    if(game.fatigue>=65)return "中1週ですが、まだ前走の疲れが抜けていません。休ませる選択も考えましょう";
    return tolerant?"中1週です。この馬なら対応できそうですが、馬体と脚元を確認して使いましょう":"中1週です。少し間隔が詰まるため、疲れが残らないか注意しましょう";
  }
  if(spacing.gap===3&&game.fatigue>=60)return "中2週ですが、まだ疲れが残っています。状態優先で判断しましょう";
  return "";
}
function shortRestAbilityPenalty(targetWeek=game.week){
  const spacing=raceIntervalState(targetWeek),tolerance=(game.turnaroundTolerance-500)/200;
  if(spacing.gap===1)return Math.max(6,Math.round(25-tolerance*8+game.raceLoad*.10));
  if(spacing.gap===2)return Math.max(2,Math.round(9-tolerance*3+game.raceLoad*.035));
  if(spacing.gap===3)return Math.max(0,Math.round(3-tolerance));
  return 0;
}
function postRaceFatigueGain(race,weather,place){
  const recovery=(game.recoveryPower-550)/100;
  const distance=Math.max(0,(race.distance-1200)/300);
  const going=["重","不良"].includes(weather.going)?4:weather.going==="稍重"?2:0;
  const effort=place<=3?2:0;
  const spacing=raceIntervalState(game.week);
  const shortRest=spacing.gap===1?8:spacing.gap===2?3:0;
  return Math.max(14,Math.min(40,Math.round(19+distance+going+effort+shortRest-recovery)));
}
function renderTack(){
  document.querySelector("#temperamentComment").textContent=trainerTemperamentComment();
  document.querySelector("#legConditionComment").textContent=legCoachComment();
  document.querySelector("#tackChoices").innerHTML=game.tackUnlocked.length
    ? `<button data-tack="" class="${!game.equippedTack?"selected":""}">馬具なし</button>`+
      game.tackUnlocked.map(id=>`<button data-tack="${id}" class="${game.equippedTack===id?"selected":""}">${tackCatalog[id].name}<small>${tackCatalog[id].desc}</small></button>`).join("")
    : "";
}
function applyHorseAppearance(el){
  if(!el)return;
  const color=game.candidate?.color||"#b96e32";
  el.style.setProperty("--active-horse-color",color);
  el.style.setProperty("--horse-color",color);
  el.querySelectorAll(".candidate-pixel-horse").forEach(horse=>horse.style.setProperty("--horse-color",color));
  el.classList.toggle("has-face-mark",!!game.candidate?.faceMark);
  el.classList.toggle("has-socks",(game.candidate?.socks||0)>0);
  ["hood","blinkers","cheekpieces"].forEach(id=>el.classList.toggle(`tack-${id}`,game.equippedTack===id));
}
function renderHorseDetail(){
  const stage=document.querySelector("#detailHorseStage");
  applyHorseAppearance(stage);
  document.querySelector("#detailAge").textContent=`${horseAge()}歳 ${game.candidate?.sex||""}・${gameYear()}年目`;
  document.querySelector("#horseDetailInfo").innerHTML=`<h2>${game.horseName}</h2><dl>
    <dt>性別・毛色</dt><dd>${game.candidate?.sex||"牡馬"}・${game.candidate?.coat||"栗毛"}${game.candidate?.faceMark?"・額に白い模様":""}</dd>
    <dt>目つき</dt><dd>${game.candidate?.eyeType||"穏やか"}</dd><dt>性格</dt><dd>${trainerTemperamentComment()}</dd>
    <dt>馬体</dt><dd>${game.weight}kg・${weightComment()}</dd><dt>馬具</dt><dd>${game.equippedTack?tackCatalog[game.equippedTack].name:"なし"}</dd>
    <dt>戦績</dt><dd>${game.races}戦${game.wins}勝・${game.prize.toLocaleString()}万円</dd><dt>好感度</dt><dd>${game.affection<3?"まだ少し緊張":game.affection<8?"心を開いてきた":"とても懐いている"}</dd></dl>`;
}
function renderLineage(){
  const sire=game.candidate?.sire?.[0]||"不明",dam=game.candidate?.dam?.[0]||"不明";
  document.querySelector("#lineageGeneration").textContent=`現在${game.generation}代目`;
  document.querySelector("#lineageCurrent").innerHTML=`<small>CURRENT HORSE・${game.generation}代目</small><h2>${game.horseName}</h2><p>${game.candidate?.sex||"牡馬"}・${game.candidate?.coat||"栗毛"}　${game.races}戦${game.wins}勝</p><div class="lineage-parents"><span><small>父</small><b>${sire}</b></span><span><small>母</small><b>${dam}</b></span></div>`;
  const history=[...game.lineage].sort((a,b)=>b.generation-a.generation);
  document.querySelector("#lineageTree").innerHTML=history.length?history.map(horse=>`<article class="lineage-horse"><i></i><div><small>${horse.generation}代目・${horse.sex||"--"}・${horse.coat||"--"}</small><h3>${horse.name}</h3><p>${horse.races}戦${horse.wins}勝　${Number(horse.prize||0).toLocaleString()}万円</p><p class="lineage-parent-names">父 ${horse.sire||"記録なし"} ／ 母 ${horse.dam||"記録なし"}</p></div></article>`).join(""):`<p class="lineage-empty">まだ継承前です。この愛馬から血統の歴史が始まります。</p>`;
}
function renderHome(message="今週の予定を決めましょう。"){
  const trainerVariants=["trainer-suit","trainer-sunglasses","trainer-cowboy","trainer-female","trainer-veteran","trainer-young"];
  document.querySelectorAll(".pixel-trainer").forEach(trainer=>{
    trainer.classList.remove(...trainerVariants);
    trainer.classList.add(trainerVariants[(game.generation-1)%trainerVariants.length]);
  });
  const homeHorseName=document.querySelector("#homeHorseName");
  homeHorseName.textContent=game.horseName;
  const horseNameLength=Array.from(game.horseName).length;
  homeHorseName.style.fontSize=horseNameLength>=11?"10px":horseNameLength>=9?"12px":horseNameLength>=7?"14px":"16px";
  document.querySelector("#homeHorseAge").textContent=`${horseAge()}歳　${game.generation}代目`;
  const sexEl=document.querySelector("#homeHorseSex");if(sexEl)sexEl.textContent=game.candidate?.sex||"";
  document.querySelector("#homeHorseClass").textContent=displayClassLabel();
  document.querySelector("#homePrize").textContent=`${game.prize.toLocaleString()}万円`;
  document.querySelector("#weekDisplay").textContent=weekLabel();
  document.querySelector("#turnsLeft").textContent=`${game.trainingsUsed}/2`;
  document.querySelector("#farmPoints").textContent=`${game.farmPoints} FP`;
  updateStableWeather();
  document.querySelector("#conditionText").textContent=`調子：${conditionLabel()}／脚元：${legLabel()}`;
  const debutWeek=Math.min(...raceCalendar.filter(r=>r.raceClass==="新馬").map(r=>r.week));
  const reservedRace=raceCalendar.find(r=>r.id===game.reservedRaceId);
  const weeksToRace=reservedRace?Math.max(0,reservedRace.week-game.week):null;
  document.querySelector("#nextRaceButtonText").textContent=reservedRace
    ? `次走：${reservedRace.name}（${weeksToRace===0?"今週":`${weeksToRace}週後`}）`
    : game.races>0?"次走予約なし":game.week<debutWeek?`新馬戦まであと${debutWeek-game.week}週`:"新馬戦へ出走できます";
  const fatigueMessage=fatigueCoachComment();
  document.querySelector("#homeMessage").textContent=message.includes(fatigueMessage)
    ? message.trim()
    : `${message} ${fatigueMessage}`.trim();
  applyHorseAppearance(document.querySelector("#trainingScene"));
  const statsEl=document.querySelector("#horseStats");
  statsEl.hidden=!developerMode;
  statsEl.innerHTML=developerMode
    ? `<div class="dev-stat-legend">数値表示：現在値 / 素質上限</div>`+statRow("スピード",game.speed,"#57c8ff")+statRow("ダッシュ",game.dash,"#ff9d43")+statRow("スタミナ",game.stamina,"#55d56b")+
      statRow("パワー",game.power,"#ef8661")+statRow("勝負根性",game.guts,"#e6c354")+
      statRow("芝適性",game.turf,"#72c45e")+statRow("ダート適性",game.dirt,"#c9915b")+
      statRow("道悪適性",game.heavyTrack,"#5aa5c8")+
      statRow("ゲート習熟",game.gateSkill,"#c7a9ef")+
      statRow("回復力",game.recoveryPower,"#73cfc4")+statRow("連闘適性",game.turnaroundTolerance,"#d9a84c")+
      `<div class="trainer-stat"><span>競走負荷</span><b>${game.raceLoad}/100</b></div>`+
      `<div class="trainer-stat"><span>調子の波</span><b>${game.condition}／${game.conditionDirection>0?"上向き":game.conditionDirection<0?"下降中":"維持"}・${game.conditionStability}型（残り${game.conditionPeakWeeks||game.conditionPhaseWeeks}週）</b></div>`
    : "";
  document.querySelector("#horseWeight").textContent=`${game.weight}kg`;
  document.querySelector("#horseWeightCondition").textContent=weightComment();
  const trainingScene=document.querySelector("#trainingScene");
  trainingScene.classList.remove("horse-vigorous","horse-normal","horse-tired","horse-exhausted");
  trainingScene.classList.add(game.fatigue>=75?"horse-exhausted":game.fatigue>=45?"horse-tired":game.fatigue<20&&game.condition>=55?"horse-vigorous":"horse-normal");
  renderTack();
  const injured=!!game.injury;
  const reservationDue=raceCalendar.some(r=>r.id===game.reservedRaceId&&r.week===game.week);
  const trainingLocked=autoTrainingActive||trainingAnimationActive||reservationDue;
  document.querySelectorAll("[data-action]").forEach(b=>b.disabled=injured||game.trainingsUsed>=2||trainingLocked);
  document.querySelector("#goRaceSelectButton").disabled=injured;
  document.querySelector("#nextWeekButton").disabled=injured;
  document.querySelector("#autoTrainingButton").disabled=injured||trainingLocked;
  document.querySelector("#voluntaryPastureButton").disabled=injured||trainingLocked;
  document.querySelector("#pastureButton").hidden=!injured;
  document.querySelector("#hotSpringButton").hidden=!game.equipment.includes("hotSpring");
  if(injured)document.querySelector("#pastureWeeks").textContent=`${game.injury.name}・${game.injury.weeks}週間を一括進行`;
  saveGame();
  const arrivedReservation=raceCalendar.find(r=>r.id===game.reservedRaceId&&r.week===game.week);
  if(arrivedReservation&&game.reservationNotifiedId!==arrivedReservation.id)queueMicrotask(()=>showReservationArrival(arrivedReservation));
  else if(game.pendingOverseasOfferId)queueMicrotask(showOverseasInvitation);
}
function closeReservationArrival(){
  const modal=document.querySelector("#reservationArrivalModal");modal.classList.remove("show");modal.setAttribute("aria-hidden","true");
}
function showReservationArrival(race){
  game.reservationNotifiedId=race.id;saveGame();
  document.querySelector("#reservationArrivalRace").textContent=`${race.course}　${race.name}`;
  document.querySelector("#reservationArrivalTitle").textContent=race.overseas?"海外GⅠの遠征週です！":"予約レースの開催週です！";
  document.querySelector("#reservationArrivalAction").textContent=race.overseas?"海外GⅠへ出走":"レース選択へ";
  document.querySelector("#reservationArrivalGuide").textContent=race.overseas?"秘密の招待レースへ直接向かいます":"予約した会場と番組を開きます";
  const modal=document.querySelector("#reservationArrivalModal");modal.classList.add("show");modal.setAttribute("aria-hidden","false");
}
function openReservedRaceWeek(race){
  if(race.overseas){closeReservationArrival();prepareRace(race);return}
  window.selectedRaceWeek=race.week;window.selectedRaceVenue=raceVenue(race);renderRaces();showScreen("raceSelectScreen");closeReservationArrival();
}
function overseasInviteReason(key){
  return key==="arc"?"宝塚記念を制した走りが欧州関係者の目に留まりました。2400mの世界最高峰、凱旋門賞へ挑戦しませんか？":
    key==="king-george"?"芝中長距離GⅠでの実績が評価されました。欧州の夏の大一番へ招待されています。":
    key==="dubai-world-cup"?"国内ダートGⅠでの勝利が評価され、ドバイワールドカップから招待が届きました。":
    key==="bc-classic"?"ダートの世界戦で通用する走りと判断され、ブリーダーズカップクラシックへ招待されました。":
    "距離適性と国内GⅠでの実績が評価され、香港国際競走から招待が届きました。";
}
function qualifyingOverseasKey(race){
  const name=race.name;
  if(/宝塚記念/.test(name))return "arc";
  if(/大阪杯|天皇賞（春）|日本ダービー/.test(name))return "king-george";
  if(/チャンピオンズカップ|東京大賞典|帝王賞|JBCクラシック/.test(name))return "dubai-world-cup";
  if(race.surface==="ダート"&&race.raceClass==="G1")return "bc-classic";
  if(race.surface==="芝"&&race.raceClass==="G1"){
    if(race.distance<=1400)return "hong-kong-sprint";
    if(race.distance<=1800)return "hong-kong-mile";
    if(race.distance<=2200)return "hong-kong-cup";
    return "hong-kong-vase";
  }
  return null;
}
function checkOverseasInvitation(race,place){
  if(place!==1||race.overseas)return;
  const key=qualifyingOverseasKey(race);if(!key)return;
  const candidates=raceCalendar.filter(item=>item.overseas&&item.id.endsWith(`-${key}`)&&item.week>game.week&&!game.declinedOverseasInvites.includes(item.id));
  const target=candidates.sort((a,b)=>a.week-b.week)[0];if(!target)return;
  game.pendingOverseasOfferId=target.id;
}
function showOverseasInvitation(){
  const race=raceCalendar.find(item=>item.id===game.pendingOverseasOfferId);if(!race)return;
  const key=race.id.replace(/^overseas-\d+-/,"");
  document.querySelector("#overseasInviteTitle").textContent=`${race.name}からの招待`;
  document.querySelector("#overseasInviteText").textContent=`${overseasInviteReason(key)} 開催は${Math.max(1,race.week-game.week)}週後です。`;
  const modal=document.querySelector("#overseasInviteModal");modal.classList.add("show");modal.setAttribute("aria-hidden","false");
}
function closeOverseasInvitation(){const modal=document.querySelector("#overseasInviteModal");modal.classList.remove("show");modal.setAttribute("aria-hidden","true")}
const training={
  turfSolo:{label:"芝・単走",fatigue:6,stats:{speed:1,turf:1}},
  turfPair:{label:"芝・併せ馬",fatigue:13,stats:{speed:1,guts:1,turf:1}},
  dirtSolo:{label:"ダート・単走",fatigue:8,stats:{stamina:1,dirt:1}},
  dirtPair:{label:"ダート・併せ馬",fatigue:15,stats:{power:1,guts:1,dirt:1}},
  hillSolo:{label:"坂路単走",fatigue:11,stats:{power:2,stamina:1,dash:.5}},
  hillPair:{label:"坂路併せ",fatigue:17,stats:{power:2,guts:1,dash:1}},
  pool:{label:"プール",fatigue:3,stats:{stamina:1}},
  gate:{label:"ゲート訓練",fatigue:5,stats:{dash:1}},
  light:{label:"軽め調整",fatigue:0,stats:{}},
  forest:{label:"森林馬道",fatigue:0,stats:{}},
  hotSpring:{label:"温泉療養",fatigue:0,stats:{}},
};
const injuries=[
  {name:"骨膜炎",minWeeks:6,maxWeeks:10,weight:44,lossChance:.18,maxLoss:1},
  {name:"軽度の管骨骨折",minWeeks:12,maxWeeks:18,weight:25,lossChance:.32,maxLoss:2},
  {name:"繋靭帯炎",minWeeks:16,maxWeeks:24,weight:19,lossChance:.45,maxLoss:3},
  {name:"浅屈腱炎",minWeeks:24,maxWeeks:36,weight:12,lossChance:.60,maxLoss:4},
];
function weightedInjury(){
  const total=injuries.reduce((sum,x)=>sum+x.weight,0);
  let roll=Math.random()*total;
  return injuries.find(x=>(roll-=x.weight)<=0)||injuries[0];
}
function injuryRisk(type){
  const intensity={turfSolo:.55,turfPair:1,dirtSolo:.65,dirtPair:1.08,hillSolo:1.05,hillPair:1.22,pool:.08,gate:.35,hotSpring:0}[type]||0;
  if(game.fatigue<45||intensity===0)return 0;
  const fatigueRisk=Math.pow((game.fatigue-50)/50,2);
  const legRisk=game.legCondition>=65?1:game.legCondition>=45?1.45:2.1;
  return Math.min(.075,(.0015+fatigueRisk*.04*intensity)*legRisk);
}
function sufferInjury(type){
  if(Math.random()>=injuryRisk(type))return null;
  const injury=weightedInjury();
  game.injury={...injury,weeks:rnd(injury.minWeeks,injury.maxWeeks)};
  return game.injury;
}
function sendToPasture(){
  if(!game.injury)return;
  const injury=game.injury;
  const weeks=injury.weeks;
  game.week+=weeks;
  game.equipment.forEach(id=>game.equipmentAge[id]=(game.equipmentAge[id]||0)+weeks);
  game.trainingsUsed=0;
  game.fatigue=0;
  game.legCondition=Math.min(100,game.legCondition+rnd(28,45));
  game.condition=Math.max(35,Math.min(70,game.condition+rnd(-5,8)));
  game.weight=Math.min(600,bestWeight()+rnd(10,22));
  const lost=[];
  ["speed","dash","stamina","power","guts"].forEach(stat=>{
    if(Math.random()<injury.lossChance){
      const amount=rnd(1,injury.maxLoss)*10;
      game[stat]=Math.max(1,Math.round((game[stat]-amount)*10)/10);
      lost.push(stat==="speed"?"スピード":stat==="dash"?"ダッシュ":stat==="stamina"?"スタミナ":stat==="power"?"パワー":"勝負根性");
    }
  });
  game.injury=null;
  const recoveryComment=lost.length
    ? `長い休養の影響でしょう。${lost.join("や")}の動きに、まだ少し物足りなさがあります。焦らず戻していきましょう。`
    : "休養は長くなりましたが、動きに大きな衰えは見られません。ここから慎重に仕上げましょう。";
  renderHome(`${injury.name}から復帰しました。${weeks}週間の放牧を終えました。 ${recoveryComment}`);
}
function voluntaryPasture(){
  if(game.injury)return sendToPasture();
  const reserved=raceCalendar.find(r=>r.id===game.reservedRaceId&&r.week>=game.week&&r.week<=game.week+4);
  if(reserved)return renderHome(`${reserved.name}を予約しています。放牧すると間に合わないため、予約を見直してください。`);
  const before={speed:game.speed,dash:game.dash,stamina:game.stamina,power:game.power,guts:game.guts};
  for(let i=0;i<4;i++)advanceWeek(true);
  game.fatigue=Math.max(0,game.fatigue-35);
  game.raceLoad=Math.max(0,game.raceLoad-45);
  game.legCondition=Math.min(100,game.legCondition+25);
  game.condition=Math.min(100,game.condition+8);
  game.weight=Math.min(600,bestWeight()+rnd(5,11));
  let decline="";
  if(Math.random()<.16){
    const stat=["speed","dash","stamina","power","guts"][rnd(0,4)],loss=rnd(4,9);
    game[stat]=Math.max(300,game[stat]-loss);
    decline=" 長く休ませた分、動きには少し鈍さがあります。";
  }
  renderHome(`4週間の放牧から戻りました。疲れと脚元はしっかり回復しています。馬体は${game.weight}kgです。${decline}`);
}
const equipmentCatalog=[
  {id:"treadmill",name:"高性能トレッドミル",cost:120,grade:"坂路設備",desc:"坂路調教のパワー成長を補助",durability:80,icon:"走"},
  {id:"walker",name:"ウォーキングマシン",cost:90,grade:"回復設備",desc:"週送り時の疲労回復+8",durability:100,icon:"歩"},
  {id:"gps",name:"GPS計測装置",cost:70,grade:"計測設備",desc:"調教失敗率を25%軽減",durability:70,icon:"測"},
  {id:"waterWalker",name:"アクアウォーカー",cost:150,grade:"水中設備",desc:"プール調教のスタミナ成長を補助",durability:75,icon:"水"},
  {id:"startingGate",name:"練習用発馬機",cost:100,grade:"基礎設備",desc:"ゲート訓練のダッシュ成長を補助",durability:110,icon:"門"},
  {id:"iceBath",name:"脚元冷却装置",cost:85,grade:"ケア設備",desc:"調教後の脚元への負担を軽減",durability:85,icon:"冷"},
  {id:"solarium",name:"馬用ソラリウム",cost:110,grade:"回復設備",desc:"週送り時に調子をわずかに整える",durability:90,icon:"陽"},
  {id:"massage",name:"振動マッサージ機",cost:130,grade:"回復設備",desc:"週送り時の疲労回復+3",durability:75,icon:"揉"},
  {id:"haySteamer",name:"飼料スチーマー",cost:80,grade:"飼養設備",desc:"馬体重をベスト体重へ戻しやすくする",durability:95,icon:"飼"},
  {id:"altitude",name:"低酸素トレーニング室",cost:220,grade:"先進設備",desc:"ダート調教のスタミナ成長を補助",durability:60,icon:"肺"},
  {id:"hotSpring",name:"馬用温泉施設",cost:260,grade:"療養設備",desc:"温泉療養を解放。週2回分で脚元と疲労を大きく回復",durability:90,icon:"湯"},
  {id:"supportShoes",name:"治療用蹄鉄セット",cost:105,grade:"装蹄設備",desc:"強い調教による脚元への負担をさらに軽減",durability:80,icon:"蹄"},
];
function equipmentCondition(item){
  const value=game.equipmentDurability[item.id]??item.durability,ratio=value/item.durability;
  return ratio>.72?"新品同様":ratio>.42?"良好":ratio>.18?"劣化しています":"故障寸前";
}
function ageEquipment(){
  const broken=[],warnings=[];
  game.equipment=[...game.equipment].filter(id=>{
    const item=equipmentCatalog.find(x=>x.id===id);
    if(!item)return false;
    game.equipmentAge[id]=(game.equipmentAge[id]||0)+1;
    let value=game.equipmentDurability[id]??item.durability;
    value=Math.max(0,value-rnd(1,2));
    const ratio=value/item.durability;
    const breakChance=ratio>.38?0:ratio>.2?.012:ratio>.08?.035:.09;
    if(value<=0||Math.random()<breakChance){broken.push(item.name);delete game.equipmentDurability[id];delete game.equipmentAge[id];return false}
    game.equipmentDurability[id]=value;
    if(ratio<=.2&&Math.random()<.35)warnings.push(`${item.name}は故障寸前です`);
    else if(ratio<=.38&&Math.random()<.18)warnings.push(`${item.name}の劣化が目立ってきました`);
    return true;
  });
  if(broken.length)return `${broken.join("、")}が故障しました。設備ショップから買い直せます。`;
  return warnings[0]||"";
}
const galleryCatalog=[
  {id:"stable",title:"はじめての入厩",trophy:"bronze",condition:()=>true,desc:"厩舎で始まった育成の日々"},
  {id:"debut",title:"ターフへ",trophy:"bronze",condition:g=>g.races>=1,desc:"記念すべき初出走"},
  {id:"firstWin",title:"初勝利",trophy:"silver",condition:g=>g.wins>=1,desc:"初めて先頭で駆け抜けた日"},
  {id:"threeWins",title:"勝利のリズム",trophy:"silver",condition:g=>g.wins>=3,desc:"通算3勝を達成"},
  {id:"fiveWins",title:"頼れる相棒",trophy:"gold",condition:g=>g.wins>=5,desc:"通算5勝を達成"},
  {id:"tenWins",title:"勝利を重ねて",trophy:"gold",condition:g=>g.wins>=10,desc:"通算10勝を達成"},
  {id:"fiveRaces",title:"競馬を覚えた",trophy:"bronze",condition:g=>g.races>=5,desc:"5戦を無事に走り抜いた"},
  {id:"veteran",title:"歴戦の相棒",trophy:"gold",condition:g=>g.races>=10,desc:"10戦を共に戦った証"},
  {id:"twentyRaces",title:"鉄馬",trophy:"record",condition:g=>g.races>=20,desc:"20戦を走った丈夫な馬"},
  {id:"turfWin",title:"緑の疾風",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&x.course.includes("芝")),desc:"芝コースで勝利"},
  {id:"dirtWin",title:"砂の王者",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&x.course.includes("ダート")),desc:"ダートコースで勝利"},
  {id:"bothSurface",title:"二刀流",trophy:"grand",condition:g=>g.raceHistory.some(x=>x.place===1&&x.course.includes("芝"))&&g.raceHistory.some(x=>x.place===1&&x.course.includes("ダート")),desc:"芝とダートの両方で勝利"},
  {id:"sprintWin",title:"電光石火",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&/1[01234]00m/.test(x.course)),desc:"1400m以下で勝利"},
  {id:"mileWin",title:"マイルの風",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&x.course.includes("1600m")),desc:"1600m戦で勝利"},
  {id:"middleWin",title:"中距離の主役",trophy:"gold",condition:g=>g.raceHistory.some(x=>x.place===1&&/(1800|2000|2200)m/.test(x.course)),desc:"1800〜2200mで勝利"},
  {id:"longWin",title:"尽きない脚",trophy:"gold",condition:g=>g.raceHistory.some(x=>x.place===1&&/(2[4-9]00|3[0-9]00)m/.test(x.course)),desc:"2400m以上で勝利"},
  {id:"mudWin",title:"泥んこの勲章",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&["重","不良"].includes(x.going)),desc:"道悪を克服して勝利"},
  {id:"rainWin",title:"雨粒を切って",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&["雨","大雨"].includes(x.weather)),desc:"雨のレースで勝利"},
  {id:"snowRace",title:"白い競馬場",trophy:"record",condition:g=>g.raceHistory.some(x=>x.weather==="雪"),desc:"珍しい雪の日に出走"},
  {id:"record",title:"時代を超えた脚",trophy:"record",condition:g=>g.raceHistory.some(x=>x.isRecord),desc:"レコードタイムを更新"},
  {id:"unbeaten3",title:"負け知らず",trophy:"grand",condition:g=>g.races>=3&&g.raceHistory.slice(0,3).every(x=>x.place===1),desc:"デビューから3連勝"},
  {id:"comeback",title:"立ち上がる力",trophy:"gold",condition:g=>g.raceHistory.some((x,i,a)=>x.place===1&&i>0&&a[i-1].place>=6),desc:"敗戦の次走で勝利"},
  {id:"twoYearWin",title:"若駒の輝き",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&x.age===2),desc:"2歳戦で勝利"},
  {id:"olderWin",title:"円熟の走り",trophy:"gold",condition:g=>g.raceHistory.some(x=>x.place===1&&x.age>=5),desc:"5歳以上で勝利"},
  {id:"equipment",title:"最新設備の力",trophy:"bronze",condition:g=>g.equipment.length>=3,desc:"設備を3種類そろえた"},
  {id:"affection10",title:"心が通じた日",trophy:"bronze",condition:g=>g.affection>=10,desc:"愛馬との絆が深まった"},
  {id:"affection30",title:"ずっと一緒",trophy:"gold",condition:g=>g.affection>=30,desc:"愛馬との強い絆"},
  {id:"secondGen",title:"受け継ぐ血",trophy:"silver",condition:g=>g.generation>=2,desc:"2代目の育成を開始"},
  {id:"thirdGen",title:"血統の芽",trophy:"gold",condition:g=>g.generation>=3,desc:"3代目まで血をつないだ"},
  {id:"fifthGen",title:"小さな王朝",trophy:"grand",condition:g=>g.generation>=5,desc:"5代目まで血をつないだ"},
  {id:"tenthGen",title:"継承の物語",trophy:"record",condition:g=>g.generation>=10,desc:"10代続く大血統"},
  {id:"million",title:"賞金王への道",trophy:"gold",condition:g=>g.prize>=10000,desc:"獲得賞金1億円を達成"},
  {id:"fiveMillion",title:"伝説の稼ぎ手",trophy:"grand",condition:g=>g.prize>=50000,desc:"獲得賞金5億円を達成"}
];
function refreshGalleryUnlocks(){
  galleryCatalog.forEach(item=>{
    if(item.condition(game)&&!game.galleryUnlocks.includes(item.id))game.galleryUnlocks.push(item.id);
  });
}
function renderHistory(){
  const totalPrize=game.raceHistory.reduce((sum,x)=>sum+x.earned,0);
  document.querySelector("#historySummary").textContent=`${game.races}戦${game.wins}勝　${totalPrize.toLocaleString()}万円`;
  const favorites=game.favoriteRaces.length
    ? `<h2 class="archive-caption">★ お気に入りレース</h2>${[...game.favoriteRaces].map((x,index)=>({x,index})).reverse().map(({x,index})=>`<article class="history-card favorite">
        <div class="history-place"><b>★</b></div>
        <div><small>${x.course}　${x.weather}／${x.going}</small><h3>${x.raceName}</h3>
        <p>勝ちタイム ${x.winnerTime}　勝ち馬 ${x.order?.[0]?.name||"--"}</p></div>
        <div class="favorite-actions"><button class="favorite-play" data-favorite-replay="${index}">再生</button><button class="favorite-delete" data-favorite-delete="${index}">削除</button></div>
      </article>`).join("")}`
    : "";
  const history=game.raceHistory.length
    ? `<h2 class="archive-caption">全戦歴</h2>${[...game.raceHistory].reverse().map((x,i)=>`<article class="history-card ${x.place===1?"winner":""}">
        <div class="history-place"><b>${x.place}</b><small>着</small></div>
        <div><small>${x.age}歳 ${x.date}　${x.course}</small><h3>${x.raceName}</h3>
        <p>${x.weather}／${x.going}　${x.time}${x.isRecord?"　NEW RECORD":""}${x.favorite?"　★お気に入り":""}</p></div>
        <strong>+${x.earned.toLocaleString()}万</strong>
      </article>`).join("")}`
    : `<p class="empty-archive">まだ出走記録がありません。</p>`;
  document.querySelector("#historyList").innerHTML=favorites+history;
}
function replayFavoriteRace(index){
  const saved=game.favoriteRaces[index];
  if(!saved?.setup)return;
  const setup={...saved.setup,replaySeed:saved.seed,archiveReplay:true};
  document.querySelector("#raceCourseTitle").textContent=saved.course;
  document.querySelector("#raceNameTitle").textContent=`${saved.raceName}・保存リプレイ`;
  showScreen("raceScreen");
  dispatchEvent(new CustomEvent("dotkeiba:prepare",{detail:setup}));
}
function deleteFavoriteRace(index){
  const saved=game.favoriteRaces[index];
  if(!saved)return;
  if(!confirm(`「${saved.raceName}」をお気に入りから削除しますか？`))return;
  game.favoriteRaces.splice(index,1);
  saveGame();
  renderHistory();
}
function renderGallery(){
  refreshGalleryUnlocks();
  const unlocked=galleryCatalog.filter(x=>game.galleryUnlocks.includes(x.id)).length;
  document.querySelector("#gallerySummary").textContent=`思い出 ${unlocked}／${galleryCatalog.length}`;
  const memoryCards=galleryCatalog.map(item=>{
    const open=game.galleryUnlocks.includes(item.id);
    return `<article class="gallery-card ${open?"unlocked":"locked"}">
      <div class="gallery-art ${open?item.trophy:""}">
        <div class="pixel-trophy"><i class="cup"></i><i class="handle left"></i><i class="handle right"></i><i class="stem"></i><i class="base"></i></div>
        <div class="pixel-winner"><i class="head"></i><i class="cap"></i><i class="body"></i><i class="arm left"></i><i class="arm right"></i><i class="leg left"></i><i class="leg right"></i></div>
        <div class="gallery-podium"></div>
        ${open?"":'<b class="gallery-lock">?</b>'}
      </div>
      <h3>${open?item.title:"？？？？"}</h3><p>${open?item.desc:"条件を達成すると解放"}</p>
    </article>`;
  }).join("");
  document.querySelector("#galleryGrid").innerHTML=memoryCards;
  saveGame();
}
let selectedTrophyGrade="G1";
function renderTrophies(grade=selectedTrophyGrade){
  selectedTrophyGrade=grade;
  const trophies=game.gradedTrophies||[],filtered=trophies.map((t,index)=>({t,index})).filter(x=>x.t.grade===grade).reverse();
  const gradeLabel=grade==="G1"?"GⅠ":grade==="G2"?"GⅡ":"GⅢ";
  document.querySelector("#trophySummary").textContent=`全${trophies.length}個　${gradeLabel} ${filtered.length}個`;
  document.querySelectorAll("[data-trophy-grade]").forEach(button=>button.classList.toggle("selected",button.dataset.trophyGrade===grade));
  document.querySelector("#trophyGrid").innerHTML=filtered.length?filtered.map(({t,index})=>`<button class="trophy-card grade-${t.grade.toLowerCase()}" data-trophy-index="${index}"><span class="trophy-cup-icon">♛</span><b>${t.raceName}</b><small>${t.date||""}</small></button>`).join(""):`<p class="empty-archive">まだ${grade==="G1"?"GⅠ":grade==="G2"?"GⅡ":"GⅢ"}のトロフィーはありません。</p>`;
  document.querySelector("#trophyHorseDetail").hidden=true;
}
function showTrophyHorse(index){
  const trophy=(game.gradedTrophies||[])[index];if(!trophy)return;
  const detail=document.querySelector("#trophyHorseDetail"),color=trophy.horseColor||"#a96232";
  detail.innerHTML=`<div class="trophy-detail-stage" style="--horse-color:${color}"><div class="candidate-pixel-horse trophy-detail-horse"><div class="candidate-body"></div><div class="candidate-neck"></div><div class="candidate-head"><i class="candidate-eye"></i><i class="candidate-ear"></i></div><div class="candidate-tail"></div><div class="candidate-leg front"></div><div class="candidate-leg back"></div><div class="winner-wreath"></div></div></div><div><small>${trophy.grade==="G1"?"GⅠ":trophy.grade==="G2"?"GⅡ":"GⅢ"} TROPHY</small><h3>${trophy.raceName}</h3><b>${trophy.horseName}</b><p>${trophy.generation}代目　${trophy.horseAge?`${trophy.horseAge}歳　`:""}${trophy.date||""}</p></div>`;
  detail.hidden=false;detail.scrollIntoView({behavior:"smooth",block:"nearest"});
}
function train(type){
  if(trainingAnimationActive&&!autoTrainingActive)return;
  if(game.injury)return renderHome(`${game.injury.name}のため調教できません。長期放牧が必要です。`);
  if(game.trainingsUsed>=2)return renderHome("今週の調教は2回終了しました。レースか翌週を選びましょう。");
  if(type==="hotSpring"){
    if(!game.equipment.includes("hotSpring"))return renderHome("温泉療養には、設備ショップの馬用温泉施設が必要です。");
    if(game.trainingsUsed>0)return renderHome("温泉療養は今週の調教2回分を使います。週の最初に選んでください。");
    const beforeLeg=game.legCondition;
    game.trainingsUsed=2;
    game.fatigue=Math.max(0,game.fatigue-rnd(28,36));
    game.raceLoad=Math.max(0,game.raceLoad-rnd(12,20));
    game.legCondition=Math.min(100,game.legCondition+rnd(18,28));
    game.condition=Math.min(100,game.condition+rnd(3,6));
    if(game.weight<bestWeight()-5)game.weight++;
    playTrainingAnimation("hotSpring","温泉療養","脚元回復");
    return renderHome(`温泉でじっくりほぐしました。脚元は「${legLabel()}」まで回復し、疲れも抜けています。${beforeLeg<45?"故障の危険は下がりましたが、次週も慎重に進めましょう。":"表情も穏やかです。"}`);
  }
  if(type==="light"||type==="forest"){
    const forest=type==="forest",before=game.condition;
    game.trainingsUsed++;
    game.fatigue=Math.max(0,game.fatigue-(forest?12:7));
    game.legCondition=Math.min(100,game.legCondition+rnd(forest?3:2,forest?7:5));
    const turnChance=forest ? .68 : .42;
    const turned=game.conditionDirection<0&&Math.random()<turnChance;
    if(turned){game.conditionDirection=1;game.conditionPhaseWeeks=forest?rnd(3,5):rnd(2,4)}
    const conditionGain=forest?rnd(2,5):rnd(1,3);
    game.condition=Math.min(100,game.condition+conditionGain);
    if(game.weight<bestWeight()-4&&Math.random()<.55)game.weight++;
    playTrainingAnimation(forest?"forest":"light",forest?"森林馬道":"軽め調整",turned?"上向き":"調整");
    const trend=turned?"調子の下降が止まり、上向く気配が出てきました。":game.condition>before?"気分転換になり、表情が少し明るくなりました。":"大きな変化はありませんが、無理なく整えられました。";
    return renderHome(`${trend} 疲れも少し抜けています。現在${game.weight}kg、${weightComment()}。`);
  }
  if(type==="rest"){
    game.trainingsUsed++;
    game.fatigue=Math.max(0,game.fatigue-28);
    game.condition=Math.min(100,game.condition+4);
    const restWeightDiff=game.weight-bestWeight();
    const restWeightGain=restWeightDiff<=-9?rnd(2,4):restWeightDiff<4?rnd(1,2):rnd(0,1);
    game.weight=Math.min(600,game.weight+restWeightGain);
    game.legCondition=Math.min(100,game.legCondition+rnd(8,14));
    playTrainingAnimation("rest","休養","回復");
    return renderHome(`${conditionTrendComment()} 休養後は${game.weight}kg、${weightComment()}。`);
  }
  const t=training[type];
  const beforeStats=Object.fromEntries(Object.keys(t.stats).map(stat=>[stat,game[stat]]));
  const roll=Math.random(),failChance=(.05+game.fatigue*.004)*(game.equipment.includes("gps")?.75:1);
  let outcome,mult;
  if(roll<failChance){outcome="失敗";mult=0}
  else if(roll>.94-game.condition*.0005){outcome="大成功";mult=2}
  else{outcome="成功";mult=1}
  Object.entries(t.stats).forEach(([stat,value])=>{
    game[stat]=Math.round((game[stat]+trainingGain(stat,value,mult,type))*10)/10;
  });
  if(type==="gate"&&mult>0)game.gateSkill=Math.min(1000,game.gateSkill+rnd(mult===2?24:12,mult===2?40:22));
  const gains=Object.fromEntries(Object.keys(t.stats).map(stat=>[stat,game[stat]-beforeStats[stat]]));
  game.trainingsUsed++; game.fatigue=Math.min(100,game.fatigue+t.fatigue);
  const rawLegLoad={turfSolo:3,turfPair:8,dirtSolo:4,dirtPair:9,hillSolo:9,hillPair:12,pool:-7,gate:2}[type]||0;
  const careReduction=(game.equipment.includes("iceBath")?2:0)+(game.equipment.includes("supportShoes")?2:0);
  const legLoad=Math.max(-7,rawLegLoad-careReduction);
  game.legCondition=Math.max(0,Math.min(100,game.legCondition-legLoad+rnd(-1,1)));
  const weightDiffBefore=game.weight-bestWeight();
  let weightLoss;
  if(weightDiffBefore<=-4){
    weightLoss=type.includes("Pair")?rnd(0,1):0;
  }else if(weightDiffBefore<=3){
    weightLoss=type.includes("Pair")?rnd(1,2):type==="hillSolo"?rnd(1,2):rnd(0,1);
  }else{
    weightLoss=type==="pool"?rnd(0,1):type==="gate"?rnd(0,1):type.includes("Pair")?rnd(2,3):type==="hillSolo"?rnd(2,3):rnd(1,2);
  }
  game.weight=Math.max(330,game.weight-weightLoss);
  game.condition=Math.max(20,Math.min(100,game.condition+(outcome==="大成功"?5:outcome==="失敗"?-10:-1)));
  const injury=sufferInjury(type);
  if(injury){
    playTrainingAnimation(type,t.label,"故障");
    return renderHome(`${t.label}中に${injury.name}を発症しました。復帰には${injury.weeks}週間の長期放牧が必要です。`);
  }
  playTrainingAnimation(type,t.label,outcome);
  game.temperamentObservations++;
  let tackMessage="";
  if(!game.temperamentKnown&&game.temperamentObservations>=2){
    game.temperamentKnown=true;
    tackMessage=` ${trainerTemperamentComment()}`;
  }
  const proposed=game.temperament==="荒い"||game.temperament==="前向き"?"blinkers":game.temperament==="臆病"?"hood":game.temperamentObservations>=4?"cheekpieces":null;
  if(proposed&&!game.tackUnlocked.includes(proposed)&&Math.random()<.38){
    game.tackUnlocked.push(proposed);
    tackMessage+=` 調教師から${tackCatalog[proposed].name}を試す提案がありました。`;
  }
  const coachComment=trainingCoachComment(type,outcome,gains);
  renderHome(`${coachComment} ${nextTrainingAdvice()} ${conditionTrendComment()} 現在${game.weight}kg、${weightComment()}。${tackMessage}`);
}
function playTrainingAnimation(type,label,outcome){
  if(autoTrainingActive)return;
  const popup=document.querySelector("#trainingPopup");
  const stage=document.querySelector("#trainingPopupStage");
  document.querySelector("#trainingPopupTitle").textContent=label;
  document.querySelector("#trainingPopupResult").textContent=outcome==="失敗"?"うまく走れなかった…":outcome==="大成功"?"大成功！":`${outcome}！`;
  popup.style.setProperty("--popup-horse-color",game.candidate?.color||"#b96e32");
  trainingAnimationActive=true;
  document.querySelectorAll("[data-action]").forEach(button=>button.disabled=true);
  document.querySelector("#autoTrainingButton").disabled=true;
  popup.classList.add("show");
  popup.setAttribute("aria-hidden","false");
  stage.className=`training-popup-stage ${type}`;
  clearTimeout(playTrainingAnimation.timer);
  playTrainingAnimation.timer=setTimeout(()=>{
    popup.classList.remove("show");
    popup.setAttribute("aria-hidden","true");
    trainingAnimationActive=false;
    renderHome(document.querySelector("#homeMessage")?.textContent?.replace(/\s+疲れ[^。]*。?$/,"" )||"今週の予定を決めましょう。");
  },1600);
}
function playAutoTrainingSequence(steps,modeName,finishText){
  const popup=document.querySelector("#trainingPopup"),stage=document.querySelector("#trainingPopupStage");
  const title=document.querySelector("#trainingPopupTitle"),result=document.querySelector("#trainingPopupResult");
  const compact=steps.filter((step,index)=>index===0||step.type!==steps[index-1].type).slice(0,5);
  const sequence=compact.length?compact:[{type:"rest",label:"休養"}];
  popup.style.setProperty("--popup-horse-color",game.candidate?.color||"#b96e32");
  trainingAnimationActive=true;
  document.querySelectorAll("[data-action]").forEach(button=>button.disabled=true);
  document.querySelector("#autoTrainingButton").disabled=true;
  popup.classList.add("show","auto-sequence");popup.setAttribute("aria-hidden","false");
  clearTimeout(playAutoTrainingSequence.timer);
  let index=0;
  const showNext=()=>{
    if(index>=sequence.length){
      title.textContent=`おまかせ調教（${modeName}）完了`;
      result.textContent=finishText;
      stage.className="training-popup-stage rest auto-finish";
      playAutoTrainingSequence.timer=setTimeout(()=>{
        popup.classList.remove("show","auto-sequence");popup.setAttribute("aria-hidden","true");
        trainingAnimationActive=false;
        renderHome(`おまかせ調教を終え、${weekLabel()}から通常調教を選べます。`);
      },850);
      return;
    }
    const step=sequence[index];
    title.textContent=`おまかせ調教 ${index+1}/${sequence.length}`;
    result.textContent=step.label;
    stage.className="training-popup-stage";
    void stage.offsetWidth;
    stage.className=`training-popup-stage ${step.type}`;
    index++;
    // おまかせはテンポを優先し、内容を判別できる約1秒で次へ切り替える。
    playAutoTrainingSequence.timer=setTimeout(showNext,1000);
  };
  showNext();
}
function advanceWeek(rest=false){
  game.week++; game.trainingsUsed=0;
  applyWeeklyPeakDecline();
  const recoveryEquipment=(game.equipment.includes("walker")?8:0)+(game.equipment.includes("massage")?3:0);
  const naturalRecovery=Math.round(18+(game.recoveryPower-550)/45);
  game.fatigue=Math.max(0,game.fatigue-(rest?naturalRecovery+24:naturalRecovery)-recoveryEquipment);
  game.raceLoad=Math.max(0,game.raceLoad-Math.round(9+game.recoveryPower/90+(rest?8:0)));
  game.legCondition=Math.min(100,game.legCondition+(rest?rnd(12,20):rnd(4,8)));
  advanceConditionCycle((rest?5:0)+(game.equipment.includes("solarium")?1:0));
  const weeklyWeightDiff=game.weight-bestWeight();
  const weeklyWeightChange=rest
    ? (weeklyWeightDiff<=-9?rnd(3,5):weeklyWeightDiff<4?rnd(1,3):rnd(0,1))
    : weeklyWeightDiff>=9?rnd(-1,0):weeklyWeightDiff>=4?rnd(0,1):weeklyWeightDiff<=-9?rnd(3,5):weeklyWeightDiff<=-4?rnd(2,3):rnd(1,2);
  game.weight=Math.max(330,Math.min(600,game.weight+weeklyWeightChange));
  if(game.condition<38)game.weight=Math.max(330,game.weight-rnd(1,2));
  if(game.condition>=68){
    const target=bestWeight();
    if(game.weight>target+3)game.weight--;
    else if(game.weight<target-3)game.weight++;
  }
  if(game.equipment.includes("haySteamer")){
    const target=bestWeight();
    if(game.weight>target+3)game.weight--;
    else if(game.weight<target-3)game.weight++;
  }
  const equipmentNotice=ageEquipment();
  const reserved=raceCalendar.find(r=>r.id===game.reservedRaceId);
  const notice=reserved&&reserved.week===game.week?` 予約していた「${reserved.name}」の開催週です。`:reserved&&reserved.week-game.week===1?` 来週は予約した「${reserved.name}」です。`:"";
  renderHome(`${notice} ${equipmentNotice} ${conditionTrendComment()}`.trim());
}
function autoTrainingChoice(mode,raceSoon=false,usage={},lastType=""){
  const weightDiff=game.weight-bestWeight();
  if(game.legCondition<48&&game.equipment.includes("hotSpring")&&game.trainingsUsed===0)return "hotSpring";
  if(game.legCondition<62)return game.trainingsUsed===0?"pool":"rest";
  if(game.fatigue>=55)return "rest";
  if(raceSoon){
    if(game.fatigue>=30)return "rest";
    if(game.condition<38&&(usage.light||0)<1)return "light";
    if(Math.abs(weightDiff)>8)return weightDiff>0?"hillSolo":"pool";
    return game.trainingsUsed===0?"turfSolo":(usage.gate||0)<2?"gate":"hillSolo";
  }
  if(mode==="safe"){
    if(game.condition<35&&(usage.light||0)<1)return "light";
    if(game.fatigue>=35)return game.trainingsUsed===0?"pool":"rest";
    if(weightDiff>=10)return "dirtSolo";
    if(weightDiff<=-10)return "pool";
  }else if(mode==="balanced"){
    const conditionCare=(usage.forest||0)+(usage.light||0);
    if(game.condition<38&&conditionCare<2)return game.trainingsUsed===0?"forest":"light";
    if(game.fatigue>=45)return "rest";
    if(weightDiff>=12)return "hillSolo";
    if(weightDiff<=-4)return game.trainingsUsed===0?"pool":"rest";
  }else if(mode==="race"){
    if(game.fatigue>=40)return "pool";
    if(weightDiff>=8)return "hillSolo";
    if(weightDiff<=-8)return "rest";
  }
  const candidates=[
    {stat:"speed",type:"turfSolo"},
    {stat:"dash",type:(usage.gate||0)<2?"gate":"hillSolo"},
    {stat:"stamina",type:game.fatigue>=28?"pool":"dirtSolo"},
    {stat:"power",type:mode==="safe"?"hillSolo":"dirtPair"},
    {stat:"guts",type:mode==="safe"?"dirtSolo":game.fatigue<24?"hillPair":"turfPair"},
    {stat:"turf",type:"turfSolo"},
    {stat:"dirt",type:"dirtSolo"},
  ];
  candidates.forEach(candidate=>{
    const repeated=(usage[candidate.type]||0)*75+(candidate.type===lastType?55:0);
    const hardPenalty=candidate.type.includes("Pair")&&game.fatigue>=30?80:0;
    candidate.score=game[candidate.stat]+repeated+hardPenalty;
  });
  candidates.sort((a,b)=>a.score-b.score);
  return candidates[0].type;
}
function runAutoTraining(mode){
  if(game.injury)return renderHome("故障中はおまかせ調教を利用できません。復帰を待ちましょう。");
  const modeName=mode==="safe"?"安全":mode==="balanced"?"バランス":"レース仕上げ";
  const beforeStats=Object.fromEntries(["speed","dash","stamina","power","guts","turf","dirt"].map(stat=>[stat,game[stat]]));
  const beforeEquipment=[...game.equipment],counts={},typeUsage={},animationSteps=[],startWeek=game.week;
  let lastAutoType="";
  let completed=0,stoppedForRace=false;
  autoTrainingActive=true;
  for(let i=0;i<4;i++){
    const reserved=raceCalendar.find(r=>r.id===game.reservedRaceId);
    if(reserved&&reserved.week===game.week){stoppedForRace=true;break}
    const raceSoon=!!reserved&&reserved.week===game.week+1;
    while(game.trainingsUsed<2&&!game.injury){
      const type=autoTrainingChoice(mode,raceSoon,typeUsage,lastAutoType),label=training[type]?.label||"休養";
      counts[label]=(counts[label]||0)+1;
      typeUsage[type]=(typeUsage[type]||0)+1;lastAutoType=type;
      animationSteps.push({type,label});
      train(type);
    }
    if(game.injury)break;
    advanceWeek(false);completed++;
    if(raceSoon){stoppedForRace=true;break}
  }
  autoTrainingActive=false;
  Object.keys(beforeStats).forEach(stat=>{
    const gain=Math.max(0,game[stat]-beforeStats[stat]);
    game[stat]=Math.round((beforeStats[stat]+gain*.8)*10)/10;
  });
  const broken=beforeEquipment.filter(id=>!game.equipment.includes(id)).map(id=>equipmentCatalog.find(x=>x.id===id)?.name).filter(Boolean);
  const menu=Object.entries(counts).map(([label,count])=>`${label}${count}回`).join("、");
  const stopText=game.injury?`${game.injury.name}を発症したため途中で中止しました。`:stoppedForRace?"予約レースの開催週です。調教は締め切られ、出走確認へ進みます。":"4週間を終えました。";
  renderHome(`おまかせ調教（${modeName}）で${game.week-startWeek}週間進めました。${menu||"調教なし"}。${stopText}${broken.length?` ${broken.join("、")}が故障しました。`:""} ${nextTrainingAdvice()}`);
  playAutoTrainingSequence(animationSteps,modeName,stopText);
  const dueRace=raceCalendar.find(r=>r.id===game.reservedRaceId&&r.week===game.week);
  if(dueRace)setTimeout(()=>showReservationArrival(dueRace),Math.min(2200,650+animationSteps.length*180));
  saveGame();
}
function renderShop(){
  document.querySelector("#shopPoints").textContent=`${game.farmPoints} FP`;
  document.querySelector("#equipmentCards").innerHTML=equipmentCatalog.map(item=>{
    const owned=game.equipment.includes(item.id),canBuy=game.farmPoints>=item.cost;
    return `<article class="equipment-card ${owned?"owned":""}">
      <div class="equipment-icon">${item.icon}</div>
      <div><small>${item.grade}</small><h3>${item.name}</h3><p>${item.desc}</p>${owned?`<b class="equipment-condition">状態：${equipmentCondition(item)}</b>`:""}</div>
      <button data-equipment="${item.id}" ${owned||!canBuy?"disabled":""}>${owned?"所有中":`${item.cost} FP`}</button>
    </article>`;
  }).join("");
}
function renderEquipmentStatus(){
  document.querySelector("#stableEquipmentCount").textContent=`${game.equipment.length}台 所有`;
  document.querySelector("#stableEquipmentList").innerHTML=game.equipment.length?game.equipment.map(id=>{
    const item=equipmentCatalog.find(x=>x.id===id);
    if(!item)return "";
    const weeks=game.equipmentAge[id]||0;
    return `<article class="stable-equipment-card"><div class="equipment-icon">${item.icon}</div><div><small>${item.grade}</small><h3>${item.name}</h3><p>購入から ${weeks}週経過</p><b>状態：${equipmentCondition(item)}</b></div></article>`;
  }).join(""):'<p class="empty-equipment">まだ設備を持っていません。設備ショップで購入できます。</p>';
}
function buyEquipment(id){
  const item=equipmentCatalog.find(x=>x.id===id);
  if(!item||game.equipment.includes(id)||game.farmPoints<item.cost)return;
  game.farmPoints-=item.cost;game.equipment.push(id);game.equipmentDurability[id]=item.durability;game.equipmentAge[id]=0;saveGame();renderShop();
}
function renderRaces(){
  if(!Number.isFinite(window.selectedRaceWeek))window.selectedRaceWeek=game.week;
  const displayWeek=Math.max(1,Math.min(CAREER_MAX_WEEKS,window.selectedRaceWeek));
  window.selectedRaceWeek=displayWeek;
  const year=Math.floor((displayWeek-1)/48)+1,yearWeek=(displayWeek-1)%48;
  const displayLabel=`${year}年目 ${Math.floor(yearWeek/4)+1}月${yearWeek%4+1}週`;
  document.querySelector("#selectTurn").textContent=displayWeek===game.week?"今週":displayWeek>game.week?`今から${displayWeek-game.week}週後`:"開催終了";
  document.querySelector("#raceWeekLabel").textContent=displayLabel;
  document.querySelector("#previousRaceWeek").disabled=displayWeek<=1;
  const periodRaces=raceCalendar.filter(r=>r.week===displayWeek&&r.program&&!r.overseas);
  const venues=[...new Set(periodRaces.map(raceVenue))];
  if(window.selectedRaceVenue&&!venues.includes(window.selectedRaceVenue))window.selectedRaceVenue="";
  if(!window.selectedRaceVenue)window.selectedRaceVenue=venues[0]||"";
  document.querySelector("#raceVenueTabs").innerHTML=venues.map(v=>`<button data-venue="${v}" class="${window.selectedRaceVenue===v?"selected":""}">${v}</button>`).join("");
  const shown=periodRaces.filter(r=>raceVenue(r)===window.selectedRaceVenue).sort((a,b)=>(a.number||11)-(b.number||11));
  document.querySelector("#raceChoices").innerHTML=shown.map(r=>{
    const arrived=r.week===game.week,debutSeasonOpen=game.week>=21;
    const targetAge=horseAgeAtWeek(r.week),ageEligible=raceAgeTextEligible(r.age||"",targetAge),sexEligible=!String(r.age||"").includes("牝")||game.candidate?.sex==="牝馬";
    const conditionEligible=r.condition(game);
    const eligible=arrived&&debutSeasonOpen&&ageEligible&&sexEligible&&conditionEligible,surfaceAbility=r.surface==="芝"?game.turf:game.dirt;
    const reservable=!arrived&&r.week>game.week&&ageEligible&&sexEligible&&conditionEligible;
    const raceYear=Math.floor((r.week-1)/48)+1,raceYearWeek=(r.week-1)%48;
    const officialDate=r.officialDate?`${Number(r.officialDate.slice(5,7))}月${Number(r.officialDate.slice(8,10))}日（2026公式）`:`${raceYear}年目 ${Math.floor(raceYearWeek/4)+1}月${raceYearWeek%4+1}週`;
    let reason="出走条件外";
    if(eligible)reason="出走する";
    else if(!arrived)reason="未来の予定";
    else if(!debutSeasonOpen)reason="2歳新馬戦の開始前";
    else if(!ageEligible)reason=`${r.age}限定`;
    else if(!sexEligible)reason="牝馬限定";
    else if(r.raceClass==="新馬"&&game.races>0)reason="新馬戦は初戦のみ";
    else if(r.raceClass==="未勝利"&&!game.maiden)reason="勝ち上がり済み";
    else if(r.id==="derby")reason="優先権・収得賞金不足";
    else if(game.maiden)reason="未勝利馬条件";
    else if(["1勝","2勝","3勝","オープン"].includes(r.raceClass))reason=`現在は${classLabel()}`;
    else reason="条件を満たしていないため除外";
    const reserved=game.reservedRaceId===r.id;
    const wonBefore=game.raceHistory.some(x=>x.raceName===r.name&&x.place===1);
    const gradedWon=["G1","G2","G3"].includes(r.raceClass)&&(wonBefore||(game.gradedTrophies||[]).some(t=>t.raceName===r.name));
    return `<article class="race-choice ${eligible?"":"locked"} ${reservable?"reservable":""} ${reserved?"reserved":""} ${gradedWon?"won-graded":""}">${gradedWon?'<span class="race-won-trophy" title="勝利済み重賞" aria-label="勝利済み重賞">🏆</span>':""}<b class="race-number">${r.number||11}R</b><div><small>${officialDate}　${r.course}${reserved?"　★出走予定":""}</small>
    <h3>${r.name}</h3><p>1着賞金 ${r.prize.toLocaleString()}万円　${r.surface} ${developerMode?surfaceAbility:scoutComment(`${r.surface}適性`,surfaceAbility)}</p></div>
    <div class="race-choice-buttons"><button ${eligible?"":"disabled"} data-race="${r.id}">${reason}</button>${reservable||reserved?`<button data-reserve="${r.id}">${reserved?"予約を解除":"出走予約"}</button>`:""}</div></article>`;
  }).join("")||`<p class="empty-races">この開催場の番組はありません。</p>`;
}
function playerAbility(race){
  const surface=race.surface==="芝"?game.turf:game.dirt;
  const speed=game.speed,dash=game.dash,stamina=game.stamina,power=game.power,guts=game.guts;
  const distanceWeight=race.distance>=2000?stamina:speed;
  const weightPenalty=Math.min(80,Math.abs(game.weight-bestWeight())*2.2);
  const fatiguePenalty=game.fatigue<=25?0:game.fatigue<=45?(game.fatigue-25)*.6:game.fatigue<=70?12+(game.fatigue-45)*1.2:42+(game.fatigue-70)*1.3;
  const distancePenalty=distanceAbilityPenalty(race.distance);
  const spacingPenalty=shortRestAbilityPenalty(game.week);
  const legPenalty=game.legCondition>=80?0:game.legCondition>=60?(80-game.legCondition)*.35:7+(60-game.legCondition)*.75;
  const raw=distanceWeight*.28+speed*.18+dash*.08+stamina*.14+power*.11+guts*.07+surface*.14+
    growthAbilityBonus()+raceConditionModifier()-weightPenalty-fatiguePenalty-distancePenalty-spacingPenalty-legPenalty;
  return Math.round(Math.min(game.generation===1?840:1000,raw));
}
function seededRaceRandom(race,salt=0){
  const text=`${game.horseName}-${race.id}-${game.week}-${salt}`;
  let hash=2166136261;
  for(let i=0;i<text.length;i++){hash^=text.charCodeAt(i);hash=Math.imul(hash,16777619)}
  return (hash>>>0)/4294967296;
}
const VENUE_WEATHER_REGION={
  "札幌":"north","函館":"north",
  "門別":"north","盛岡":"north",
  "福島":"east","新潟":"east",
  "東京":"kanto","中山":"kanto",
  "浦和":"kanto","船橋":"kanto","大井":"kanto","川崎":"kanto",
  "金沢":"central","名古屋":"central",
  "園田":"kansai","高知":"west","佐賀":"west",
  "中京":"central","京都":"kansai","阪神":"kansai","小倉":"west"
};
const MONTHLY_RAIN_CHANCE={
  north:[.18,.17,.19,.22,.25,.28,.27,.30,.31,.28,.24,.20],
  east:[.17,.18,.22,.27,.31,.38,.36,.34,.38,.28,.20,.17],
  kanto:[.14,.16,.21,.27,.31,.43,.35,.30,.39,.28,.17,.13],
  central:[.16,.18,.23,.28,.33,.42,.37,.32,.40,.29,.18,.15],
  kansai:[.17,.19,.23,.28,.32,.40,.36,.31,.38,.27,.18,.15],
  west:[.19,.21,.25,.29,.32,.39,.36,.34,.38,.27,.20,.18]
};
function raceCalendarMonth(race){
  return Math.floor(((race.week-1)%48)/4)+1;
}
function raceDayWeather(race){
  const venue=raceVenue(race),month=raceCalendarMonth(race);
  const region=VENUE_WEATHER_REGION[venue]||"kanto";
  let rainChance=MONTHLY_RAIN_CHANCE[region][month-1];
  // 梅雨と秋雨は雨が増えるが、連続して極端な道悪ばかりにはしない。
  if(month===6&&(region==="kanto"||region==="central"||region==="kansai"))rainChance+=.04;
  const weatherRoll=seededRaceRandom(race,1);
  const heavyRainChance=month>=7&&month<=9?.16:.09;
  const snowChance=region!=="north"&&(month===1||month===2||month===12)
    // 1レース単位ではごく低確率。複数年プレイして約3年に1度見る程度のレア演出。
    ? (region==="east"||region==="kanto"?.006:.004)
    : 0;
  const snow=seededRaceRandom(race,5)<snowChance;
  const weather=snow?"雪":weatherRoll<rainChance
    ? (seededRaceRandom(race,3)<heavyRainChance?"大雨":"雨")
    : weatherRoll<rainChance+.27?"曇":"晴";
  const goingRoll=seededRaceRandom(race,2);
  const priorMoisture=seededRaceRandom(race,4);
  let going;
  if(weather==="晴"){
    const damp=priorMoisture<rainChance*.38;
    going=damp?(goingRoll<.62?"良":"稍重"):(goingRoll<.94?"良":"稍重");
  }else if(weather==="曇"){
    const damp=priorMoisture<rainChance*.65;
    going=damp?(goingRoll<.40?"良":goingRoll<.84?"稍重":"重"):(goingRoll<.72?"良":"稍重");
  }else if(weather==="雪"){
    going=goingRoll<.42?"稍重":goingRoll<.86?"重":"不良";
  }else if(weather==="雨"){
    going=goingRoll<.08?"良":goingRoll<.48?"稍重":goingRoll<.86?"重":"不良";
  }else{
    going=goingRoll<.12?"稍重":goingRoll<.57?"重":"不良";
  }
  return {weather,going,month,region};
}
function updateStableWeather(){
  const scene=document.querySelector(".stable-scene");
  if(!scene)return;
  const stableForecast=game.week===1
    ? {weather:"晴",going:"良",month:1,region:"kanto"}
    : raceDayWeather({id:`stable-${game.week}-${game.generation||1}`,week:game.week,course:"東京 芝1600m"});
  scene.classList.remove("weather-cloudy","weather-rain","weather-heavy-rain","weather-snow");
  if(stableForecast.weather==="曇")scene.classList.add("weather-cloudy");
  if(stableForecast.weather==="雨")scene.classList.add("weather-rain");
  if(stableForecast.weather==="大雨")scene.classList.add("weather-rain","weather-heavy-rain");
  if(stableForecast.weather==="雪")scene.classList.add("weather-snow");
  const label=document.querySelector("#stableWeatherLabel");
  if(label)label.textContent=stableForecast.weather==="曇"?"くもり":stableForecast.weather;
}
function prepareRace(race){
  if(!race)return;
  const leftTracks=new Set(["東京","中京","新潟","盛岡","浦和","船橋","川崎"]);
  document.querySelector("#raceCourseTitle").textContent=`${race.course}・${leftTracks.has(raceVenue(race))?"左":"右"}`;
  document.querySelector("#raceNameTitle").textContent=race.name;
  document.querySelector("#newspaperDate").textContent=weekLabel();
  document.querySelector("#newspaperCourse").textContent=race.course;
  document.querySelector("#newspaperRaceName").textContent=race.name;
  document.querySelector("#newspaperEntries").innerHTML='<p class="newspaper-loading">出走各馬を取材中……</p>';
  showScreen("newspaperScreen");
  try{
    const timingRecord=raceTimingRecord(race),benchmarkTime=classBenchmarkTime(race),recordTime=timingRecord.time;
    const raceWeather=raceDayWeather(race);
    // condition関数を含むカレンダー本体ではなく、結果処理に必要な値だけを保存する。
    game.selectedRace={
      id:race.id,name:race.name,raceClass:race.raceClass,course:race.course,
      surface:race.surface,distance:race.distance,prize:race.prize,
      trialRight:race.trialRight||null,overseas:!!race.overseas
    };
    game.currentRaceWeather=raceWeather;
    saveGame();
    dispatchEvent(new CustomEvent("dotkeiba:prepare",{detail:{horseName:game.horseName,raceName:race.name,age:horseAge(),ability:playerAbility(race),dash:game.dash,gateSkill:game.gateSkill,condition:game.condition,fatigue:game.fatigue,difficulty:race.difficulty*10,raceClass:race.raceClass,overseas:!!race.overseas,venue:raceVenue(race),distance:race.distance,surface:race.surface,direction:race.direction||null,courseAuditMode:!!race.courseAuditMode,heavyTrack:game.heavyTrack,temperament:game.temperament,temperamentValue:game.temperamentValue,equippedTack:game.equippedTack,weather:raceWeather.weather,going:raceWeather.going,raceMonth:raceWeather.month,baseTime:benchmarkTime,benchmarkTime,recordTime,recordVerified:timingRecord.verified,layoutV2:true}}));
  }catch(error){
    console.error("race preparation failed",error);
    document.querySelector("#commentary").textContent="レースの読み込みを再試行しています。";
    dispatchEvent(new CustomEvent("dotkeiba:prepare",{detail:{
      horseName:game.horseName,raceName:race.name,age:horseAge(),ability:playerAbility(race),dash:game.dash,gateSkill:game.gateSkill,
      condition:game.condition,fatigue:game.fatigue,difficulty:race.difficulty*10,
      raceClass:race.raceClass,overseas:!!race.overseas,venue:raceVenue(race),distance:race.distance,direction:race.direction||null,courseAuditMode:!!race.courseAuditMode,
      surface:race.surface,heavyTrack:game.heavyTrack,weather:"晴",going:"良",
      raceMonth:raceCalendarMonth(race),baseTime:race.baseTime,
      benchmarkTime:race.baseTime,recordTime:race.baseTime*.965,recordVerified:false
    }}));
  }
}
function resultRaceReview(race,player,place,pace){
  const comments=[];
  if(place===1)comments.push(player.style==="逃げ"?"自分のリズムで運び、最後までよく粘り切りました":player.style==="先行"?"好位から安定した競馬ができました":player.style==="差し"?"道中で脚をため、直線でしっかり伸びました":"後方で我慢し、終いの脚を生かせました");
  else if(place<=3)comments.push("勝ち切れませんでしたが、内容のある競馬でした");
  else comments.push(player.style==="逃げ"?"前半に脚を使い、最後は苦しくなりました":player.style==="先行"?"好位にはつけましたが、直線でもうひと伸びが必要です":player.style==="差し"?"直線では伸びましたが、前との差を詰め切れませんでした":"後方から運びましたが、追い出してから届きませんでした");
  if(player.temperamentTrouble==="出遅れ")comments.push("スタートの遅れが位置取りに響きました。ゲート訓練を続けたいですね");
  else if(player.temperamentTrouble==="掛かり")comments.push("道中で掛かって余計な力を使いました。折り合いが今後の課題です");
  else if(player.temperamentTrouble==="物見")comments.push("物見をして集中を欠く場面がありました。馬具も含めて対策を考えます");
  else if(pace&&pace.includes("ハイ")&&player.style==="逃げ")comments.push("速い流れを先頭で受けた分、終いが厳しくなりました");
  else if(pace&&pace.includes("スロー")&&(player.style==="差し"||player.style==="追込"))comments.push("前が止まらない流れで、脚質的にも厳しい展開でした");
  comments.push(raceSuitabilityAdvice(race,place));
  return comments.join("。 ");
}
function postRaceTrainerComment(){
  const comments=[];
  if(game.injury)return `調教師「レース後に${game.injury.name}が判明しました。無理はできません。${game.injury.weeks}週間の長期放牧が必要です。 ${game.lastRaceAdvice||""}」`;
  if(game.fatigue>=75)comments.push("かなり疲れが残っています。次週は休養を優先した方がいいでしょう");
  else if(game.fatigue>=52)comments.push("レースの疲れが見えます。強い調教は避けたいところです");
  else comments.push("レース後としては疲れも軽く、回復は早そうです");

  const weightDiff=game.weight-bestWeight();
  if(weightDiff<=-12)comments.push("馬体が細くなっています。しっかり食べさせて戻しましょう");
  else if(weightDiff>=12)comments.push("まだ馬体には余裕があります");
  else comments.push("馬体重は良い範囲に収まっています");

  if(game.legCondition<45)comments.push("脚元に強い張りがあります。念のため慎重に見ていきます");
  else if(game.legCondition<70)comments.push("脚元に少し張りがあるので、軽めの調整がよさそうです");
  else comments.push("脚元に大きな問題はありません");

  comments.push(recoveryTraitComment());
  if(game.raceLoad>=75)comments.push("最近の競走負荷がかなり重なっています。間隔を空けて疲れを抜きたいところです");
  else if(game.raceLoad>=45)comments.push("ここ数走の負荷が少し蓄積しています。次走までの間隔には注意しましょう");
  comments.push(conditionTrendComment());
  if(game.lastRaceAdvice)comments.push(game.lastRaceAdvice);
  return `調教師「${comments.join("。")}。」`;
}
function sufferPostRaceInjury(race,going){
  let risk=.0005;
  if(game.fatigue>=70)risk+=.0012;
  if(game.legCondition<70)risk+=.0010;
  if(game.legCondition<45)risk+=.0025;
  if(["重","不良"].includes(going))risk+=.0008;
  if(race.surface==="ダート")risk+=.0003;
  const spacing=raceIntervalState(game.week);
  const toleranceFactor=Math.max(.55,Math.min(1.5,(850-game.turnaroundTolerance)/350));
  if(spacing.gap===1)risk+=.006*toleranceFactor;
  else if(spacing.gap===2)risk+=.0018*toleranceFactor;
  if(game.raceLoad>=75)risk+=(game.raceLoad-70)*.00012;
  if(Math.random()>=Math.min(.025,risk))return null;
  const injury=weightedInjury();
  game.injury={...injury,weeks:rnd(injury.minWeeks,injury.maxWeeks)};
  return game.injury;
}
function showResult(detail){
  const player=detail.order.find(h=>h.player),place=detail.order.findIndex(h=>h.player)+1,r=game.selectedRace;
  const earned=place===1?r.prize:place===2?Math.round(r.prize*.4):place===3?Math.round(r.prize*.25):place<=5?Math.round(r.prize*.1):0;
  game.prize+=earned;game.races++;if(place===1){game.wins++;game.maiden=false}
  if(game.reservedRaceId===r.id)game.reservedRaceId=null;
  const classMoneyAdd=place===1
    ? (r.raceClass==="新馬"||r.raceClass==="未勝利"?400:r.raceClass==="1勝"?500:r.raceClass==="2勝"?600:r.raceClass==="3勝"?900:r.raceClass==="G3"?1600:r.raceClass==="G2"||r.raceClass==="G1"?Math.round(r.prize*.5):1000)
    : ((["G1","G2","G3"].includes(r.raceClass)&&place===2)?Math.round(r.prize*.2):0);
  game.classMoney+=classMoneyAdd;
  if(r.trialRight&&place<=r.trialRight.maxPlace&&!game.priorityRights.includes(r.trialRight.name))game.priorityRights.push(r.trialRight.name);
  const fpTable=[45,32,24,18,14,11,9,7];
  const fpEarned=fpTable[Math.min(7,place-1)]+5;
  game.farmPoints+=fpEarned;
  const weather=game.currentRaceWeather||{weather:"晴",going:"良"};
  const playerTrouble=player.temperamentTrouble;
  if(playerTrouble==="掛かり"&&!game.tackUnlocked.includes("blinkers"))game.tackUnlocked.push("blinkers");
  if((playerTrouble==="出遅れ"||playerTrouble==="物見")&&!game.tackUnlocked.includes("hood"))game.tackUnlocked.push("hood");
  game.raceHistory.push({
    raceName:r.name,raceClass:r.raceClass,course:r.course,place,time:player.finishTime,split1000:detail.split1000,final3F:player.final3F,
    earned,weather:weather.weather,going:weather.going,isRecord:!!player.isRecord,
    age:horseAge(),date:weekLabel(),week:game.week,favorite:false
  });
  if(place===1&&["G1","G2","G3"].includes(r.raceClass))game.gradedTrophies.push({raceName:r.name,grade:r.raceClass,horseName:game.horseName,horseAge:horseAge(),horseColor:game.candidate?.color||"#a96232",horseCoat:game.candidate?.coat||"栗毛",generation:game.generation,date:weekLabel()});
  checkOverseasInvitation(r,place);
  refreshGalleryUnlocks();
  const spacingBeforeRace=raceIntervalState(game.week);
  const fatigueGain=postRaceFatigueGain(r,weather,place);
  game.fatigue=Math.min(100,game.fatigue+fatigueGain);advanceConditionCycle(-8);
  const raceLoadGain=Math.round(25+r.distance/250+(spacingBeforeRace.gap===1?18:spacingBeforeRace.gap===2?7:0));
  game.raceLoad=Math.min(100,game.raceLoad+raceLoadGain);
  game.legCondition=Math.max(0,game.legCondition-rnd(4,9));
  game.weight=Math.max(330,game.weight-rnd(4,7));
  sufferPostRaceInjury(r,weather.going);
  game.lastRaceWeek=game.week;
  game.lastRaceAdvice=raceSuitabilityAdvice(r,place);
  game.week++;game.trainingsUsed=0;saveGame();
  document.querySelector("#resultPlace").textContent=`${place}着`;document.querySelector("#resultHorseName").textContent=game.horseName;
  document.querySelector("#resultFrame").textContent=player.id;document.querySelector("#resultFrame").style.background=player.color;
  const resultHorseScene=document.querySelector("#resultHorseScene");
  resultHorseScene.classList.remove("is-winner","is-placed","is-defeated");
  resultHorseScene.classList.add(place===1?"is-winner":place<=3?"is-placed":"is-defeated");
  resultHorseScene.setAttribute("aria-label",place===1?"優勝レイを掛けて喜ぶ愛馬":place<=3?"健闘して少し悔しそうな愛馬":"レースに敗れて悲しむ愛馬");
  const winnerResult=detail.order[0],gapMs=Math.max(0,(player.finishMs||0)-(winnerResult.finishMs||0));
  const resultPhraseGroups=place===1
    ?{mood:["やったね！","最高の走り！","よくやった！","見事な勝利！"],comment:["最後まで力強く走り切りました。立派な勝利です！","今日はこの馬の良さを存分に出せました。","堂々と先頭でゴールしました！","素晴らしい内容です。この勢いで次も狙いましょう！"]}
    :place===2&&gapMs<=500
      ?{mood:["あと少しだった！","惜しかった！","次は届くよ！","悔しいね！"],comment:["勝ち馬とはわずかな差でした。もうひと伸びできれば逆転できます。","最後まで競り合いました。次こそ先頭でゴールしましょう。","本当に惜しい内容です。力は十分通用しています。","あと一歩でした。この悔しさを次のレースへつなげましょう。"]}
      :place<=3
        ?{mood:["次こそ勝とう！","よく食らいついた！","まだ伸びるよ！","立派な好走！"],comment:["上位争いに加わる良い走りでした。","最後まで諦めず、しっかり伸びています。","勝ち切るにはもう少しですが、内容は悪くありません。","このクラスでも戦える手応えがありました。"]}
        :place<=5
          ?{mood:["もうひと頑張り！","次は上を狙おう！","悪くないよ！","ここから巻き返そう！"],comment:["掲示板には入りました。展開が向けばさらに上を狙えます。","大きくは崩れていません。次走での前進に期待しましょう。","見せ場は作れました。足りない部分を調教で補いましょう。","相手なりに走れています。もう一段階成長させたいところです。"]}
          :{mood:["もっと頑張ろう！","次は巻き返そう！","今日は残念！","また挑戦しよう！","ここからだよ！"],comment:["今日は力を出し切れませんでした。状態を整えてやり直しましょう。","悔しい結果ですが、原因を見直せば巻き返せます。","この経験も次につながります。焦らず立て直しましょう。","まだ成長の余地があります。得意条件を探していきましょう。","今日は展開も向きませんでした。次走でもう一度挑戦しましょう。"]};
  const phraseIndex=(game.races+game.week+place+player.id)%resultPhraseGroups.mood.length;
  document.querySelector("#resultHorseMood").textContent=resultPhraseGroups.mood[phraseIndex];
  applyHorseAppearance(resultHorseScene);
  document.querySelector("#resultTime").textContent=player.finishTime;
  document.querySelector("#resultSplit1000").textContent=detail.split1000||"--:--.-";
  document.querySelector("#resultFinal3F").textContent=player.final3F||"--.-秒";
  document.querySelector("#resultPrize").textContent=`${(earned*10000).toLocaleString()}円`;
  document.querySelector("#resultFP").textContent=`${fpEarned}`;
  document.querySelector("#postRaceCondition").textContent=resultRaceReview(r,player,place,detail.measuredPace);
  document.querySelector("#resultOrder").innerHTML=detail.order.slice(0,5).map((h,i)=>`<div><span>${i+1}</span><b>${h.name}</b><small>${h.odds.toFixed(1)}倍</small></div>`).join("");
  showScreen("resultScreen");
}

document.querySelector("#continueButton").disabled=!hasAnySave();
document.querySelector("#devModeButton").textContent=developerMode?"開発表示 ON":"開発表示";
document.querySelector("#newGameButton").onclick=()=>{renderSaveSlots("new");showScreen("saveSlotScreen")};
const raceTestVenue=document.querySelector("#raceTestVenue"),raceTestDirection=document.querySelector("#raceTestDirection"),raceTestDirectionRow=document.querySelector("#raceTestDirectionRow"),raceTestSurface=document.querySelector("#raceTestSurface"),raceTestDistance=document.querySelector("#raceTestDistance");
const TEST_SURFACE_LABEL={turf:"芝",dirt:"ダート",banei:"ばんえい"};
// NAR公式コースレコードに掲載されている施行実績距離。検証画面だけで使用する。
const TEST_LOCAL_DISTANCES={
  "帯広":{ばんえい:[200]},
  "門別":{ダート:[1000,1100,1200,1500,1600,1700,1800,2000]},
  "盛岡":{芝:[1000,1600,1700,2400],ダート:[1000,1200,1400,1600,1800,2000,2500,3000]},
  "水沢":{ダート:[850,1300,1400,1600,1800,1900,2000,2500]},
  "浦和":{ダート:[800,1300,1400,1500,1600,1900,2000]},
  "船橋":{ダート:[1000,1200,1500,1600,1700,1800,2200,2400]},
  "大井":{ダート:[1000,1200,1400,1500,1600,1650,1700,1800,2000,2400,2600]},
  "川崎":{ダート:[900,1400,1500,1600,2000,2100]},
  "金沢":{ダート:[900,1300,1400,1500,1700,1900,2000,2100,2600]},
  "笠松":{ダート:[800,1400,1800,1900,2500]},
  "名古屋":{ダート:[900,920,1400,1500,1700,2000,2100]},
  "園田":{ダート:[820,1230,1400,1700,1870,2400]},
  "姫路":{ダート:[800,1400,1500,1800,2000]},
  "高知":{ダート:[800,1300,1400,1600,1800,1900,2400]},
  "佐賀":{ダート:[900,1300,1400,1750,1800,1860,2000,2500]}
};
function raceTestBaseVenue(venue){return venue}
function raceTestSurfaceDistances(venue,surface){
  const baseVenue=raceTestBaseVenue(venue);
  if(JRA_COURSE_DISTANCES[baseVenue]?.[surface])return JRA_COURSE_DISTANCES[baseVenue][surface];
  if(TEST_LOCAL_DISTANCES[baseVenue]?.[surface])return TEST_LOCAL_DISTANCES[baseVenue][surface];
  const course=window.COURSE_LAYOUTS?.[baseVenue],english=surface==="芝"?"turf":surface==="ダート"?"dirt":"banei";
  const direct=course?.distances?.[english];if(Array.isArray(direct)&&direct.length)return [...new Set(direct)].sort((a,b)=>a-b);
  const fromStarts=Object.keys(course?.startPositions||{}).filter(key=>key.startsWith(english)).map(key=>Number(key.match(/_(\d+)$/)?.[1])).filter(Number.isFinite);
  return [...new Set(fromStarts)].sort((a,b)=>a-b);
}
function updateRaceTestSummary(){
  const venue=raceTestVenue.value,baseVenue=raceTestBaseVenue(venue),surface=raceTestSurface.value,distance=Number(raceTestDistance.value),course=window.COURSE_LAYOUTS?.[baseVenue];
  if(!course)return;
  const english=surface==="芝"?"turf":surface==="ダート"?"dirt":"banei",layoutKey=Object.keys(course.layouts).find(k=>k===english)||Object.keys(course.layouts).find(k=>k.startsWith(english));
  const lap=course.lap[layoutKey]||course.lap[english]||Object.values(course.lap)[0],straight=course.straight[layoutKey]||course.straight[english]||Object.values(course.straight)[0];
  const selectedDirection=raceTestDirection.value||course.direction;
  const direction=selectedDirection==="left"?"左回り":selectedDirection==="right"?"右回り":selectedDirection==="both"?"左右両回り":"直線";
  document.querySelector("#raceTestCourseSummary").innerHTML=`<b>${venue}競馬場　${surface}${distance}m</b><br>${direction}／1周 ${lap}m／直線 ${straight}m<br>高低差 ${course.elevation}m　${course.corner}<br><small>本編と同じコース表示</small>`;
}
function updateRaceTestDistances(){
  const distances=raceTestSurfaceDistances(raceTestVenue.value,raceTestSurface.value);
  raceTestDistance.innerHTML=distances.map(distance=>`<option value="${distance}">${distance}m</option>`).join("");updateRaceTestSummary();
}
function updateRaceTestSurfaces(){
  const course=window.COURSE_LAYOUTS?.[raceTestBaseVenue(raceTestVenue.value)],surfaces=course?.surfaces||["turf","dirt"];
  const directions=course?.direction==="both"?[{value:"right",label:"右回り（外回り）"},{value:"left",label:"左回り（外回り）"}]:[{value:course?.direction||"left",label:course?.direction==="right"?"右回り":course?.direction==="straight"?"直線":"左回り"}];
  raceTestDirection.innerHTML=directions.map(item=>`<option value="${item.value}">${item.label}</option>`).join("");
  raceTestDirectionRow.hidden=directions.length===1;
  raceTestSurface.innerHTML=surfaces.map(surface=>`<option value="${TEST_SURFACE_LABEL[surface]}">${TEST_SURFACE_LABEL[surface]}</option>`).join("");updateRaceTestDistances();
}
function openRaceTestSetup(){
  const venues=Object.keys(window.COURSE_LAYOUTS||{});raceTestVenue.innerHTML=venues.map(venue=>`<option value="${venue}" ${venue==="東京"?"selected":""}>${venue}</option>`).join("");
  updateRaceTestSurfaces();showScreen("raceTestSetupScreen");
}
document.querySelector("#raceTestButton").onclick=openRaceTestSetup;
raceTestVenue.onchange=updateRaceTestSurfaces;raceTestSurface.onchange=updateRaceTestDistances;raceTestDistance.onchange=updateRaceTestSummary;
raceTestDirection.onchange=updateRaceTestSummary;
document.querySelector("#raceTestStartButton").onclick=()=>{
  const venue=raceTestVenue.value,surface=raceTestSurface.value,distance=Number(raceTestDistance.value),direction=raceTestDirection.value||null;
  const baseVenue=raceTestBaseVenue(venue);
  game=defaultGame();generateCandidate();
  const c=game.candidate,testAbility={speed:650,dash:620,stamina:640,power:610,guts:600,turf:660,dirt:620};
  const testCaps=createPotentialCaps({...c,...testAbility});
  game={...game,horseName:"ドットスター",week:21,...testAbility,gateSkill:600,heavyTrack:560,baseBestWeight:c.baseBestWeight,weight:c.baseBestWeight,condition:72,candidate:c,potentialCaps:testCaps};
  const testRace={id:`test-${baseVenue}-${surface}-${distance}`,week:game.week,name:"コース検証テスト",raceClass:"オープン",course:`${baseVenue} ${surface}${distance}m`,surface,distance,direction,courseAuditMode:true,baseTime:surface==="ばんえい"?150000:Math.round((surface==="芝"?60000:63000)*distance/1000),prize:0,difficulty:82,condition:()=>true};
  prepareRace(testRace);showScreen("raceScreen");dispatchEvent(new CustomEvent("dotkeiba:auto-start"));
};
document.querySelector("#rerollHorseButton").onclick=generateCandidate;
document.querySelector("#birthContinueButton").onclick=()=>showScreen("nameScreen");
document.querySelector("#continueButton").onclick=()=>{renderSaveSlots("continue");showScreen("saveSlotScreen")};
document.querySelector("#saveSlotList").onclick=e=>{
  const button=e.target.closest("[data-save-slot]");if(!button)return;
  const slot=Number(button.dataset.saveSlot),mode=e.currentTarget.dataset.mode,existing=saveSlotSummary(slot);
  if(mode==="continue"){
    if(!existing)return;
    if(loadGame(slot)){renderHome();showScreen("homeScreen")}return;
  }
  if(existing&&!confirm(`セーブ${slot}の「${existing.horseName}」に上書きして、新しく始めますか？`))return;
  activeSaveSlot=slot;localStorage.setItem(ACTIVE_SLOT_KEY,String(slot));localStorage.removeItem(saveSlotKey(slot));
  game=defaultGame();document.querySelector("#rerollHorseButton").hidden=false;generateCandidate();showScreen("nameScreen");
};
document.querySelector("#confirmNameButton").onclick=()=>{
  const input=document.querySelector("#horseNameInput"),name=input.value.trim();
  const blocked=["チンコ","マンコ","セックス","シネ","コロス"];
  if(!/^[ァ-ヶー]{2,10}$/.test(name)||blocked.some(word=>name.includes(word))){
    document.querySelector("#nameScreen .hint").textContent="馬名はカタカナ2〜10文字で、使用できない表現を含まない名前にしてください。";
    input.focus();return;
  }
  const c=game.candidate,legacy={generation:game.generation,farmPoints:game.farmPoints,equipment:[...game.equipment],equipmentDurability:{...game.equipmentDurability},equipmentAge:{...game.equipmentAge},galleryUnlocks:[...game.galleryUnlocks],gradedTrophies:[...(game.gradedTrophies||[])],favoriteRaces:[...game.favoriteRaces],lineage:[...game.lineage],retirementRecords:[...game.retirementRecords],inheritanceComment:c.inheritanceComment||""};game={...defaultGame(),...legacy,horseName:name,speed:c.speed,dash:c.dash,gateSkill:c.gateSkill,stamina:c.stamina,power:c.power,guts:c.guts,turf:c.turf,dirt:c.dirt,heavyTrack:c.heavyTrack,temperament:c.temperament,temperamentValue:c.temperamentValue,baseBestWeight:c.baseBestWeight,weight:c.weight,growthType:c.growthType,growthPotential:c.growthPotential,potentialCaps:c.potentialCaps,distanceMin:c.distanceMin,distanceMax:c.distanceMax,recoveryPower:c.recoveryPower,turnaroundTolerance:c.turnaroundTolerance,condition:c.condition,conditionDirection:c.conditionDirection,conditionPhaseWeeks:c.conditionPhaseWeeks,conditionStability:c.conditionStability,conditionPeakWeeks:c.conditionPeakWeeks,candidate:c};
  renderHome(`入厩しました。現在${game.weight}kg、${weightComment()}。${game.generation>1?game.inheritanceComment:"まずは馬体を整えましょう。"}`);showScreen("homeScreen");
};
document.querySelectorAll("[data-back]").forEach(b=>b.onclick=()=>showScreen(b.dataset.back));
document.querySelectorAll("[data-action]").forEach(b=>b.onclick=()=>train(b.dataset.action));
document.querySelector("#pastureButton").onclick=sendToPasture;
document.querySelector("#voluntaryPastureButton").onclick=voluntaryPasture;
document.querySelector("#nextWeekButton").onclick=()=>advanceWeek(false);
const autoTrainingModal=document.querySelector("#autoTrainingModal");
const closeAutoTrainingModal=()=>{autoTrainingModal.classList.remove("show");autoTrainingModal.setAttribute("aria-hidden","true")};
document.querySelector("#autoTrainingButton").onclick=()=>{
  autoTrainingModal.classList.add("show");autoTrainingModal.setAttribute("aria-hidden","false");
};
document.querySelector("#autoTrainingCancel").onclick=closeAutoTrainingModal;
autoTrainingModal.onclick=e=>{if(e.target===autoTrainingModal)closeAutoTrainingModal()};
document.querySelectorAll("[data-auto-mode]").forEach(button=>button.onclick=()=>{
  const mode=button.dataset.autoMode;
  closeAutoTrainingModal();
  runAutoTraining(mode);
});
document.querySelector("#shopButton").onclick=()=>{renderShop();showScreen("shopScreen")};
const openStableEquipment=()=>{renderEquipmentStatus();showScreen("stableEquipmentScreen")};
document.querySelector("#stableBuilding").onclick=openStableEquipment;
document.querySelector("#stableBuilding").onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();openStableEquipment()}};
document.querySelector("#historyButton").onclick=()=>{renderHistory();showScreen("historyScreen")};
document.querySelector("#historyList").onclick=e=>{
  const deleteButton=e.target.closest("[data-favorite-delete]");
  if(deleteButton){deleteFavoriteRace(Number(deleteButton.dataset.favoriteDelete));return}
  const replayButton=e.target.closest("[data-favorite-replay]");
  if(replayButton)replayFavoriteRace(Number(replayButton.dataset.favoriteReplay));
};
document.querySelector("#galleryButton").onclick=()=>{renderGallery();showScreen("galleryScreen")};
document.querySelector("#trophyButton").onclick=()=>{renderTrophies("G1");showScreen("trophyScreen")};
document.querySelector("#trophyTabs").onclick=e=>{const button=e.target.closest("[data-trophy-grade]");if(button)renderTrophies(button.dataset.trophyGrade)};
document.querySelector("#trophyGrid").onclick=e=>{const button=e.target.closest("[data-trophy-index]");if(button)showTrophyHorse(Number(button.dataset.trophyIndex))};
const openHorseDetail=()=>{renderHorseDetail();showScreen("horseDetailScreen")};
document.querySelector("#lineageButton").onclick=()=>{renderLineage();showScreen("lineageScreen")};
document.querySelector("#homeHorse").onclick=e=>{e.stopPropagation();openHorseDetail()};
document.querySelector("#homeHorse").onkeydown=e=>{
  if(e.key!=="Enter"&&e.key!==" ")return;
  e.preventDefault();e.stopPropagation();openHorseDetail();
};
document.querySelector("#trainingScene").onclick=()=>{
  game.affection=Math.min(99,game.affection+1);
  const reactions=["嬉しそうに首を振りました。","こちらへ駆け寄ってきました。","小さく跳ねて喜んでいます。","鼻を寄せて甘えています。"];
  renderHome(reactions[rnd(0,reactions.length-1)]);
};
document.querySelector("#detailHorseStage").onclick=()=>{
  game.affection=Math.min(99,game.affection+1);
  const reactions=["ブルルッ、と嬉しそうです。","撫でると目を細めました。","もっと遊んでほしそうに見ています。","尻尾を振って応えてくれました。"];
  document.querySelector("#horseReaction").textContent=reactions[rnd(0,reactions.length-1)];
  document.querySelector("#detailHorseStage").classList.remove("horse-happy");void document.querySelector("#detailHorseStage").offsetWidth;document.querySelector("#detailHorseStage").classList.add("horse-happy");
  saveGame();
};
document.querySelector("#retireHorseButton").onclick=()=>{renderRetirement();showScreen("retirementScreen")};
let pendingBreedingPartner=null;
function closeInheritanceConfirm(){
  pendingBreedingPartner=null;
  const modal=document.querySelector("#inheritConfirmModal");
  modal.classList.remove("show");modal.setAttribute("aria-hidden","true");
}
document.querySelector("#breedingPartners").onclick=e=>{
  const button=e.target.closest("[data-breeding-partner]");
  if(!button)return;
  const partner=currentBreedingChoices[Number(button.dataset.breedingPartner)];
  if(!partner||game.prize<partner.cost)return;
  pendingBreedingPartner=partner;
  document.querySelector("#inheritConfirmText").textContent=`${game.horseName}を引退させ、${partner.name}との子で次世代を始めます。よろしいですか？`;
  const modal=document.querySelector("#inheritConfirmModal");
  modal.classList.add("show");modal.setAttribute("aria-hidden","false");
};
document.querySelector("#inheritConfirmProceed").onclick=()=>{const partner=pendingBreedingPartner;closeInheritanceConfirm();if(partner)beginNextGeneration(partner)};
document.querySelector("#inheritConfirmCancel").onclick=closeInheritanceConfirm;
document.querySelector("#overseasInviteAccept").onclick=()=>{
  const race=raceCalendar.find(item=>item.id===game.pendingOverseasOfferId);if(!race)return closeOverseasInvitation();
  game.reservedRaceId=race.id;game.reservationNotifiedId=null;game.pendingOverseasOfferId=null;saveGame();closeOverseasInvitation();
  renderHome(`${race.name}からの招待を受けました。${Math.max(1,race.week-game.week)}週後の海外遠征へ向けて仕上げましょう。`);
};
document.querySelector("#overseasInviteDecline").onclick=()=>{
  if(game.pendingOverseasOfferId&&!game.declinedOverseasInvites.includes(game.pendingOverseasOfferId))game.declinedOverseasInvites.push(game.pendingOverseasOfferId);
  game.pendingOverseasOfferId=null;saveGame();closeOverseasInvitation();renderHome("海外からの招待は今回は見送りました。国内路線へ戻ります。");
};
document.querySelector("#devModeButton").onclick=()=>{
  developerMode=!developerMode;
  localStorage.setItem("dotKeibaDeveloperMode",developerMode?"1":"0");
  document.querySelector("#devModeButton").textContent=developerMode?"開発表示 ON":"開発表示";
  renderHome(developerMode?"内部能力と素質上限を表示しています。":"調教師コメント表示に戻しました。");
};
document.querySelector("#equipmentCards").onclick=e=>{if(e.target.dataset.equipment)buyEquipment(e.target.dataset.equipment)};
document.querySelector("#tackChoices").onclick=e=>{
  const button=e.target.closest("[data-tack]");
  if(!button)return;
  game.equippedTack=button.dataset.tack||null;
  renderHome(game.equippedTack?`${tackCatalog[game.equippedTack].name}を装着しました。`:"馬具を外しました。");
};
document.querySelector("#goRaceSelectButton").onclick=()=>{
  const reserved=raceCalendar.find(r=>r.id===game.reservedRaceId&&r.week===game.week);
  window.selectedRaceWeek=game.week;window.selectedRaceVenue=reserved?raceVenue(reserved):"";renderRaces();showScreen("raceSelectScreen");
};
document.querySelector("#reservationArrivalOpen").onclick=()=>{
  const reserved=raceCalendar.find(r=>r.id===game.reservedRaceId);
  if(reserved)openReservedRaceWeek(reserved);else closeReservationArrival();
};
document.querySelector("#reservationArrivalClose").onclick=closeReservationArrival;
document.querySelector("#raceChoices").onclick=e=>{
  const reserve=e.target.closest("[data-reserve]");
  if(reserve){game.reservedRaceId=game.reservedRaceId===reserve.dataset.reserve?null:reserve.dataset.reserve;game.reservationNotifiedId=null;saveGame();renderRaces();return}
  const button=e.target.closest("[data-race]");
  if(button){
    const race=raceCalendar.find(r=>r.id===button.dataset.race),warning=raceSpacingCoachWarning(race?.week);
    if(warning){
      pendingRaceAfterSpacingWarning=race;
      document.querySelector("#raceSpacingWarningText").textContent=warning+"。どうしますか？";
      const modal=document.querySelector("#raceSpacingWarningModal");
      modal.classList.add("show");modal.setAttribute("aria-hidden","false");
      return;
    }
    prepareRace(race);
  }
};
function closeRaceSpacingWarning(){
  pendingRaceAfterSpacingWarning=null;
  const modal=document.querySelector("#raceSpacingWarningModal");
  modal.classList.remove("show");modal.setAttribute("aria-hidden","true");
}
document.querySelector("#raceSpacingProceed").onclick=()=>{
  const race=pendingRaceAfterSpacingWarning;
  closeRaceSpacingWarning();
  if(race)prepareRace(race);
};
document.querySelector("#raceSpacingCancel").onclick=closeRaceSpacingWarning;
document.querySelector("#raceVenueTabs").onclick=e=>{const b=e.target.closest("[data-venue]");if(b){window.selectedRaceVenue=b.dataset.venue;renderRaces()}};
document.querySelector("#previousRaceWeek").onclick=()=>{window.selectedRaceWeek=Math.max(1,(window.selectedRaceWeek||game.week)-1);window.selectedRaceVenue="";renderRaces()};
document.querySelector("#nextRaceWeek").onclick=()=>{window.selectedRaceWeek=Math.min(CAREER_MAX_WEEKS,(window.selectedRaceWeek||game.week)+1);window.selectedRaceVenue="";renderRaces()};
document.querySelector("#newspaperRaceButton").onclick=()=>{showScreen("raceScreen");dispatchEvent(new CustomEvent("dotkeiba:auto-start"))};
addEventListener("dotkeiba:preview-ready",e=>{
  if(!game.selectedRace)return;
  const marks=["◎","○","▲","△","△","☆","",""];
  document.querySelector("#newspaperBias").textContent=`${e.detail.weather}・${e.detail.going}　${e.detail.bias}`;
  document.querySelector("#newspaperEntries").innerHTML=e.detail.entries.map(h=>{
    const mark=marks[h.popularity-1]||"";
    const styleKey=h.style==="追込"?"追":h.style==="先行"?"先":h.style==="差し"?"差":"逃";
    const runningStyleChart=`<div class="news-running-style" aria-label="脚質 ${h.style}"><small>脚質</small>${["逃","先","差","追"].map(label=>`<span class="${label===styleKey?"selected":""}"><i>${label}</i><b>${label===styleKey?"◀":""}</b></span>`).join("")}</div>`;
    return `<article class="newspaper-entry ${h.player?"player":""}">
      <span class="news-number frame-${h.id}">${h.id}</span><b class="news-mark">${mark}</b>
      <div><h3>${h.name}${h.player?' <small>愛馬</small>':""}</h3>${runningStyleChart}<p>調子 ${h.condition}</p><small>${h.comment}</small></div>
      <strong>${h.odds.toFixed(1)}<small>倍</small></strong>
    </article>`;
  }).join("");
});
document.querySelector("#resetGameButton").onclick=()=>{if(confirm(`セーブ${activeSaveSlot}の育成データを消しますか？`)){localStorage.removeItem(saveSlotKey(activeSaveSlot));game=defaultGame();document.querySelector("#continueButton").disabled=!hasAnySave();showScreen("titleScreen")}};
document.querySelector("#returnHomeButton").onclick=()=>{renderHome(postRaceTrainerComment().replace(/^調教師「|」$/g,""));showScreen("homeScreen")};
addEventListener("dotkeiba:finished",e=>showResult(e.detail));
addEventListener("dotkeiba:favorite",e=>{
  const favorite={...e.detail,savedAt:Date.now()};
  game.favoriteRaces.push(favorite);
  saveGame();
  const button=document.querySelector("#favoriteRaceButton");
  if(button){button.textContent="★ 保存済み";button.disabled=true}
});
addEventListener("dotkeiba:archive-close",()=>{
  renderHistory();
  showScreen("historyScreen");
});
addEventListener("dotkeiba:test-back",()=>{
  updateRaceTestSummary();
  showScreen("raceTestSetupScreen");
});

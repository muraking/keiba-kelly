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
const winnerPopup = document.querySelector("#winnerPopup");
const benchmarkTimesEl = document.querySelector("#benchmarkTimes");
const weatherDisplayEl = document.querySelector("#weatherDisplay");
const winnerReplayButton = document.querySelector("#winnerReplayButton");
const favoriteRaceButton = document.querySelector("#favoriteRaceButton");
const showResultButton = document.querySelector("#showResultButton");

// JRAの枠色：1白、2黒、3赤、4青、5黄、6緑、7橙、8桃
const COLORS = ["#f5f3e8", "#151515", "#d93732", "#2879d8", "#efc52d", "#36a852", "#e87822", "#ec73ad"];
const NAMES = ["サンライズ", "ホープフル", "ブルーギア", "ゴールドラン", "グリーンベル", "チェリーミスト", "オレンジロード", "パープルエース"];
const STYLE_PATTERNS = [
  ["逃げ", "先行", "差し", "先行", "差し", "追込", "差し", "追込"],
  ["逃げ", "逃げ", "先行", "先行", "差し", "差し", "追込", "追込"],
  ["逃げ", "逃げ", "逃げ", "先行", "差し", "差し", "追込", "追込"],
  ["逃げ", "先行", "先行", "先行", "差し", "差し", "差し", "追込"],
];
let TOTAL = 2400;
// The finish line is fixed. Each start is calculated backwards from the
// official lap length, so different distances no longer share one start.
// On this path, .349 is the end of the home straight (just before turn 1).
const FINISH_LINE_PROGRESS = .349;
let LAP = 2083.1;
let FINISH_PROGRESS = FINISH_LINE_PROGRESS;
let START_PROGRESS = FINISH_PROGRESS - TOTAL / LAP;
// 東京芝2400mを約2分24秒で走破する基礎速度。
// 2:20.3のコースレコードから通常のダービー水準2:23〜2:26を想定。
let BASE_PROGRESS_PER_MS = (TOTAL / LAP) / 144000;

let horses = [];
let state = "ready";
let multiplier = 1;
let lastTime = 0;
let raceClock = 0;
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
let opponentAbilities = [];
let fieldAverageAbility = 920;
let raceSeed = 1;
let randomState = 1;
let simulationAccumulator = 0;
let resultDispatchedForRace = false;
let pendingResultDetail = null;
let archiveReplay = false;
let horizontalLayout = false;
let layoutV2 = false;
let playerNumber = 1;
let visionRanks = new Map();
let visionRankStamp = 0;
const BASE_PLAYBACK_RATE = 4;
let playerSetup = { horseName: "ドットスター", ability: 940, dash: 550, gateSkill:450, condition: 60, fatigue: 10, difficulty: 840, heavyTrack:500, temperament:"普通",temperamentValue:50,equippedTack:null,weather:"晴", going:"良", baseTime: 144000 };

function setCommentary(message,reset=false){
  if(reset)commentaryHistory=[];
  if(!message)return;
  if(commentaryHistory[commentaryHistory.length-1]!==message)commentaryHistory.push(message);
  commentaryHistory=commentaryHistory.slice(-4);
  commentaryEl.textContent=commentaryHistory.join("\n");
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
};
function trackProfile(){return TRACK_PROFILES[currentRaceVenue]||TRACK_PROFILES["東京"]}
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
};
function configureCourseDistance(){
  const laps=COURSE_LAPS[currentRaceVenue]||COURSE_LAPS["東京"];
  LAP=laps[raceSurface]||laps["芝"];
  FINISH_PROGRESS=FINISH_LINE_PROGRESS;
  START_PROGRESS=FINISH_PROGRESS-TOTAL/LAP;
}
function trackBiasFor(number,style){
  const profile=trackProfile();
  const shortFactor=TOTAL<=1400?1.35:TOTAL<=1800?1.12:TOTAL>=2400?.72:1;
  const dirtFactor=raceSurface==="ダート"?1.18:1;
  const insideScore=(4.5-number)/3.5;
  const styleScore=style==="逃げ"?1:style==="先行"?.55:style==="差し"?-.35:-.75;
  return 1+profile.innerBias*insideScore*shortFactor*dirtFactor+profile.frontBias*styleScore*shortFactor;
}
function trackBiasLabel(){
  const profile=trackProfile();
  const frame=profile.innerBias>=.011?"内枠有利":profile.innerBias<=.003?"枠差小":"やや内枠向き";
  const run=profile.frontBias>=.009?"前有利":profile.frontBias<=-.004?"差し向き":"脚質差小";
  return `${frame}・${run}`;
}

function makeHorse(i, styles) {
  const isPlayer = i === playerNumber-1;
  const opponentIndex=i-(i>playerNumber-1?1:0);
  const opponentAbility = opponentAbilities[opponentIndex] ?? playerSetup.ability;
  return {
    id: i + 1,
    name: isPlayer ? playerSetup.horseName : NAMES[i],
    color: COLORS[i],
    style: styles[i],
    progress: START_PROGRESS - i * .0009,
    // 基本は内ラチ沿い。逃げ・先行ほど内、差し・追込も道中は馬群内で脚をためる。
    lane: styles[i] === "逃げ" ? 7.25 : styles[i] === "先行" ? 6.45 - (i % 2) * .35 : 5.75 - (i % 3) * .35,
    targetLane: styles[i] === "逃げ" ? 7.25 : styles[i] === "先行" ? 6.45 - (i % 2) * .35 : 5.75 - (i % 3) * .35,
    stamina: 1,
    ability: isPlayer ? playerSetup.ability : opponentAbility,
    heavyTrack: isPlayer ? playerSetup.heavyTrack : 400 + Math.round(raceRandom()*350),
    dash: isPlayer ? playerSetup.dash : 460 + ((i * 70) % 200),
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
    temperamentValue:isPlayer?playerSetup.temperamentValue:35+Math.round(raceRandom()*45),
    equippedTack:isPlayer?playerSetup.equippedTack:null,
    temperamentTrouble:null,
    gateChecked:false,
    temperamentRoll:raceRandom(),
    flowFit: 1,
    trackBias:trackBiasFor(i+1,styles[i]),
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

function resetRace() {
  clearTimeout(gateStartTimer);
  cancelAnimationFrame(raf);
  randomState = raceSeed;
  simulationAccumulator = 0;
  const styles = STYLE_PATTERNS[raceSeed % STYLE_PATTERNS.length];
  opponentAbilities = buildOpponentAbilities();
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
      id:h.id,name:h.name,style:h.style,odds:h.odds,popularity:h.popularity,player:h.player,
      condition:h.condition>=1.008?"絶好":h.condition>=1.002?"好調":h.condition>=.994?"普通":"下降",
      comment:h.trackBias>1.01?"枠とコース相性が魅力":h.ability>=fieldAverageAbility+25?"地力上位、勝ち負け必至":h.style==="逃げ"&&racePace.escapeCount===1?"単騎なら粘り込み十分":h.style==="追込"&&racePace.escapeCount>=3?"流れ向けば末脚炸裂":"展開ひとつで上位争い"
    }))
  }}));
  state = "ready";
  raceClock = 0;
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
  pauseButton.textContent = "一時停止";
  multiplier = 1;
  speedButton.textContent = "速度 標準";
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
  const splitNoise = (raceRandom() - .5) * 700;
  const finishNoise = (raceRandom() - .5) * 1800;
  const distanceBase = playerSetup.baseTime || TOTAL * 62;
  const baseSplit = distanceBase * 1000 / TOTAL;
  if (escapeCount >= 3) {
    return {
      name: "ハイペース",
      escapeCount,
      targetSplit: baseSplit - 1200 + splitNoise,
      targetFinish: distanceBase - 300 + finishNoise,
    };
  }
  if (escapeCount === 2) {
    return {
      name: "ややハイ",
      escapeCount,
      targetSplit: baseSplit - 500 + splitNoise,
      targetFinish: distanceBase + finishNoise,
    };
  }
  if (escapeCount === 1) {
    return {
      name: "スローペース",
      escapeCount,
      targetSplit: baseSplit + 500 + splitNoise,
      targetFinish: distanceBase + 600 + finishNoise,
    };
  }
  return {
    name: "超スロー",
    escapeCount,
    targetSplit: baseSplit + 1400 + splitNoise,
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
  const paceControl = Math.max(.74, Math.min(1.20, 1 + paceError / 240));
  if (split1000Time === null && leaderDistance >= 1000) {
    split1000Time = raceClock;
    measuredPace = classify1000mPace(split1000Time);
    split1000El.textContent = formatTime(split1000Time);
    paceDisplayEl.textContent = `実測：${measuredPace}（1000m ${formatTime(split1000Time)}）`;
    setCommentary(`1000m通過 ${formatTime(split1000Time)}、${measuredPace}！`);
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
    let velocity = BASE_PROGRESS_PER_MS * paceControl * abilityFactor * eliteFactor * goingFactor * h.condition * h.trackBias *
      styleFactor * dashFactor * temperamentFactor * tackFactor * curvePenalty * slopePenalty * kick * noise * troubleFactor * flowFactor;

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
  phaseEl.textContent =
    remaining === 0 ? "確定" :
    remaining <= 525 ? "最後の直線" :
    remaining <= 850 ? "4コーナー" :
    remaining <= 1200 ? "向正面" : "レース中";
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
      raceSeed,setup:{...playerSetup},
      order:order().map(h=>({
        id:h.id,name:h.name,color:h.color,odds:h.odds,
        finishTime:formatTime(h.finishTime),player:h.player,
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

function coursePoint(progress, lane = 3) {
  let p = ((progress % 1) + 1) % 1;
  if(trackProfile().turn==="右")p=(1-p)%1;
  if(horizontalLayout){
    const inset=lane*4,left=43+inset,right=317-inset,top=50+lane*3,bottom=230-lane*3;
    const cy=(top+bottom)/2,rx=Math.max(28,48-inset*.12),straight=.39,curve=.11;
    if(p<straight){const t=p/straight;return{x:left+(right-left)*t,y:top,angle:0,curve:false}}
    if(p<straight+curve){const t=(p-straight)/curve,a=-Math.PI/2+t*Math.PI;return{x:right+Math.cos(a)*rx,y:cy+Math.sin(a)*(bottom-top)/2,angle:a+Math.PI/2,curve:true}}
    if(p<straight*2+curve){const t=(p-straight-curve)/straight;return{x:right-(right-left)*t,y:bottom,angle:Math.PI,curve:false}}
    const t=(p-straight*2-curve)/curve,a=Math.PI/2+t*Math.PI;
    return{x:left+Math.cos(a)*rx,y:cy+Math.sin(a)*(bottom-top)/2,angle:a+Math.PI/2,curve:true};
  }
  const pt=verticalCoursePoint(p,lane);
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
  drawMarker(START_PROGRESS,"#35dc5c","START");drawMarker(FINISH_PROGRESS%1,"#ec3d35","GOAL");
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
  const isDirt=raceSurface==="ダート";
  ctx.fillStyle="#0d1a26";ctx.fillRect(0,0,LOGICAL_WIDTH,logicalHeight);
  // コース帯の芝生下地。
  ctx.fillStyle="#2d7131";ctx.fillRect(0,42,360,208);
  for(let i=0;i<44;i++){
    const x=(i*83)%356,y=46+(i*47)%200;
    ctx.fillStyle=i%3?"#245f27":"#347b32";ctx.fillRect(x,y,3,3);
  }
  // コース上部のレース情報。
  ctx.fillStyle="#101a21";ctx.fillRect(0,0,360,20);
  ctx.fillStyle="#fff3a6";ctx.font="bold 12px sans-serif";ctx.textAlign="center";
  ctx.fillText(`${playerSetup.raceName||"テストレース"}　${currentRaceVenue}${raceSurface}${TOTAL}m　${playerSetup.going}`,180,14);
  // ホーム直線沿いの大型スタンド（上辺）。
  ctx.fillStyle="#6e8492";ctx.fillRect(4,20,352,5);
  ctx.fillStyle="#506574";ctx.fillRect(4,25,352,7);
  ctx.fillStyle="#37475c";ctx.fillRect(4,32,352,10);
  const crowdCount=playerSetup.raceClass==="G1"?230:playerSetup.raceClass==="G2"?180:playerSetup.raceClass==="G3"?135:playerSetup.raceClass==="オープン"?90:45;
  const crowdColors=["#e65b4f","#f0d56a","#5ca6d8","#f2eee0","#7356a8"];
  for(let i=0;i<crowdCount;i++){
    ctx.fillStyle=crowdColors[i%5];
    ctx.fillRect(6+(i*6.1)%348,23+((i*13)%4)*4,3,3);
  }
  const trace=(lane,color,width)=>{
    ctx.beginPath();
    for(let i=0;i<=180;i++){const q=coursePoint(i/180,lane);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y)}
    ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.stroke();
  };
  trace(4.5,"#f1ead2",40);
  trace(4.5,isDirt?"#a87549":"#43943e",33);
  for(let lane=1;lane<=8;lane++)trace(lane,isDirt?(lane%2?"#c18a58":"#94613d"):(lane%2?"#65ad55":"#378537"),1);
  // 内馬場。
  ctx.beginPath();
  for(let i=0;i<=120;i++){const q=coursePoint(i/120,9.4);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y)}
  ctx.closePath();ctx.fillStyle="#1e5d28";ctx.fill();
  const profile=trackProfile();
  if(["museum","pond","sea"].includes(profile.facility)){
    ctx.fillStyle="#4d9dc1";ctx.fillRect(96,120,34,12);ctx.fillRect(104,116,18,4);
  }
  ctx.fillStyle="#9fd6a0";ctx.font="bold 9px sans-serif";ctx.textAlign="center";
  trace(8.7,"#fffdf0",2);
  drawMarker(START_PROGRESS,"#35dc5c","START");
  drawMarker(FINISH_PROGRESS%1,"#ec3d35","GOAL");

  // コース直下の実況帯（最新4行）。
  const commentaryY=254;
  ctx.fillStyle="#071018";ctx.fillRect(4,commentaryY,352,74);
  ctx.strokeStyle="#d7c35d";ctx.lineWidth=2;ctx.strokeRect(4,commentaryY,352,74);
  ctx.fillStyle="#35251c";ctx.fillRect(12,commentaryY+10,17,5);ctx.fillRect(11,commentaryY+14,3,10);
  ctx.fillStyle="#d8a06e";ctx.fillRect(13,commentaryY+15,14,15);
  ctx.fillStyle="#25201d";ctx.fillRect(16,commentaryY+20,2,2);ctx.fillRect(23,commentaryY+20,2,2);
  ctx.fillStyle="#a96644";ctx.fillRect(20,commentaryY+23,2,2);
  ctx.fillStyle="#6f2d28";ctx.fillRect(17,commentaryY+27,7,Math.floor(raceClock/260)%2===0?2:1);
  ctx.fillStyle="#f3f0df";ctx.fillRect(11,commentaryY+32,18,28);
  ctx.fillStyle="#285a91";ctx.fillRect(11,commentaryY+41,18,19);
  ctx.fillStyle="#d7c35d";ctx.fillRect(26,commentaryY+44,7,2);
  const commentaryLines=commentaryHistory.slice(-4);
  ctx.font="bold 11px sans-serif";ctx.textAlign="left";
  commentaryLines.forEach((line,index)=>{
    const aboutPlayer=line.includes(playerSetup.horseName)||line.includes("愛馬");
    ctx.fillStyle=aboutPlayer?"#ffe45c":"#f4f6f2";
    const clipped=line.length>28?`${line.slice(0,27)}…`:line;
    ctx.fillText(clipped,38,commentaryY+15+index*17);
  });

  // ターフビジョン（コース外・独立パネル）。
  const visionOrder=order(),leader=visionOrder[0];
  const vx=4,vy=330,vw=352,vh=228;
  ctx.fillStyle="#101a21";ctx.fillRect(vx,vy,vw,vh);
  ctx.strokeStyle="#d7c35d";ctx.lineWidth=3;ctx.strokeRect(vx,vy,vw,vh);
  ctx.fillStyle="#263a2e";ctx.fillRect(vx+3,vy+3,vw-6,18);
  ctx.fillStyle="#fff3a6";ctx.font="bold 12px sans-serif";ctx.textAlign="center";
  ctx.fillText("TURF VISION　中継映像",180,vy+16);
  // 中継カメラ：全馬の実走距離とコース取りをそのまま投影する。
  const camY=vy+23,camH=52;
  ctx.fillStyle=isDirt?"#9a6c43":"#4a9945";ctx.fillRect(vx+3,camY,vw-6,camH);
  ctx.fillStyle=isDirt?"#8a5f3a":"#3f8a3b";
  for(let i=0;i<12;i++)ctx.fillRect(vx+8+i*29,camY+6+(i*17)%40,18,2);
  const leaderDist=raceDistance(leader);
  const visionDistances=horses.map(h=>raceDistance(h));
  const visionFront=Math.max(...visionDistances);
  [...horses].filter(h=>visionFront-raceDistance(h)<=105).sort((a,b)=>b.lane-a.lane).forEach(h=>{
    const distance=raceDistance(h);
    const x=Math.round(vx+vw-30-(visionFront-distance)*2.65);
    const lane=Math.max(1,Math.min(8,h.lane));
    const y=Math.round(camY+11+(lane-1)*(camH-20)/7);
    drawVisionCandidateHorse(x,y,h,.38);
  });
  // 馬名タグ：先頭と自分の馬（仕様：ビジョンに愛馬の馬番と馬名を表示）。
  // 全頭順位ボード：枠色チップ＋馬番＋馬名フル表示＋着差。
  const boardY=camY+camH+4;
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

  drawMarker(START_PROGRESS, "#35dc5c", "START");
  drawMarker(FINISH_PROGRESS % 1, "#ec3d35", "GOAL");
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
  if(!leader||state!=="running"||raceDistance(leader)/TOTAL<=.50)return;
  const ratio=raceDistance(leader)/TOTAL;
  const calls=ratio>.82?["差せー！","粘れー！","そのまま！","伸びろー！","届いてくれ！","逃げ切れ！","並んだ！","もう少し！","いけー！","突き抜けろ！"]:ratio>.62?["外から来た！","内を突け！","前が開いた！","進路を取れ！","動き出した！","差を詰めろ！","いい脚だ！","馬群を割れ！"]:["いいぞー！","前を追え！","落ち着いて！","いい手応え！","まだ我慢！","行けるぞ！","頑張れー！"];
  const cycle=5200,visibleFor=2400,slot=Math.floor(cheerClock/cycle);
  if(cheerClock%cycle>=visibleFor)return;
  // レイアウトV2はコースが上部の横長帯なので、吹き出しもコース帯の中に収める。
  const spots=layoutV2
    ?[{x:8,y:22,w:104},{x:128,y:22,w:104},{x:248,y:22,w:104}]
    :[{x:226,y:54,w:108},{x:232,y:96,w:102},{x:218,y:220,w:116},{x:225,y:285,w:109},{x:216,y:350,w:118}];
  const spot=spots[(slot*3+raceSeed)%spots.length],call=calls[(slot*7+raceSeed)%calls.length];
  ctx.save();
  ctx.shadowColor="#000b";ctx.shadowBlur=0;ctx.shadowOffsetX=3;ctx.shadowOffsetY=3;
  ctx.fillStyle="#ffffff";ctx.strokeStyle="#262015";ctx.lineWidth=3;
  ctx.fillRect(spot.x,spot.y,spot.w,24);ctx.strokeRect(spot.x,spot.y,spot.w,24);
  ctx.beginPath();
  if(layoutV2){const tx=spot.x+spot.w/2;ctx.moveTo(tx-7,spot.y+24);ctx.lineTo(tx,49);ctx.lineTo(tx+7,spot.y+24)}
  else{ctx.moveTo(spot.x+spot.w,spot.y+9);ctx.lineTo(349,spot.y+15);ctx.lineTo(spot.x+spot.w,spot.y+19)}
  ctx.closePath();ctx.fill();ctx.stroke();
  ctx.shadowColor="transparent";ctx.fillStyle="#111";ctx.font="bold 11px sans-serif";ctx.textAlign="center";ctx.fillText(call,spot.x+spot.w/2,spot.y+17);
  ctx.restore();
}

function drawWeather(){
  if(!["雨","大雨","雪"].includes(playerSetup.weather))return;
  const snow=playerSetup.weather==="雪";
  const count=snow?34:playerSetup.weather==="大雨"?75:48;
  ctx.save();
  // レイアウトV2ではビジョン・高低差パネルに雨雪を重ねず、コース帯だけに降らせる。
  if(layoutV2){ctx.beginPath();ctx.rect(0,20,360,232);ctx.clip();}
  ctx.globalAlpha=snow?.82:.52;
  ctx.strokeStyle=snow?"#ffffff":"#bce8ff";
  ctx.fillStyle="#ffffff";
  ctx.lineWidth=snow?1:2;
  for(let i=0;i<count;i++){
    const x=(i*47+(raceClock*.035*(snow?.35:1)))%380-10;
    const y=(i*83+(raceClock*.06*(snow?.45:1)))%530-15;
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
  if (state === "running") {
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

startButton.addEventListener("click", () => {
  if (state === "ready") {
    state = "gates";
    startButton.disabled = true;
    pauseButton.disabled = true;
    phaseEl.textContent = "全馬ゲートイン";
    setCommentary("全馬ゲートイン。場内が静まり返ります。まもなくスタートです。");
    draw();
    gateStartTimer=setTimeout(()=>{
      if(state!=="gates")return;
      state="running";pauseButton.disabled=false;phaseEl.textContent="スタート";
      setCommentary(racePace.escapeCount >= 2
        ? `ゲートオープン！ 逃げ${racePace.escapeCount}頭が先手を争います！`
        : "ゲートオープン！ 逃げ馬がすんなり先頭へ立ちました。");
      lastTime=0;raf=requestAnimationFrame(loop);
    },1800);
  }
});

pauseButton.addEventListener("click", () => {
  state = state === "paused" ? "running" : "paused";
  pauseButton.textContent = state === "paused" ? "再開" : "一時停止";
  phaseEl.textContent = state === "paused" ? "停止中" : "レース中";
});

speedButton.addEventListener("click", () => {
  multiplier = multiplier === 1 ? 2 : multiplier === 2 ? 4 : 1;
  speedButton.textContent = multiplier === 1 ? "速度 標準" : `速度 ×${multiplier}`;
});

resetButton.addEventListener("click", resetRace);
window.addEventListener("dotkeiba:auto-start",()=>{if(state==="ready")startButton.click()});
winnerReplayButton.addEventListener("click",()=>{
  resetRace();
  state="running";
  startButton.disabled=true;
  pauseButton.disabled=false;
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
  TOTAL = event.detail.distance || 2400;
  configureCourseDistance();
  BASE_PROGRESS_PER_MS = (TOTAL / LAP) / (event.detail.baseTime || TOTAL * 62);
  resetRace();
});

resetRace();

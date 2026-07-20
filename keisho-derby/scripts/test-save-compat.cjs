const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {SCHEMA_VERSION,migrateSaveData,copyLegacySave}=require(path.join(__dirname,"..","save-compat.js"));

const defaults={
  saveVersion:SCHEMA_VERSION,horseName:"",week:1,trainingsUsed:0,prize:0,farmPoints:0,equipment:[],priorityRights:[],
  speed:0,dash:0,stamina:0,power:0,guts:0,turf:0,dirt:0,raceHistory:[],favoriteRaces:[],galleryUnlocks:["stable"],
  gradedTrophies:[],tackUnlocked:[],declinedOverseasInvites:[],lineage:[],retirementRecords:[],equipmentDurability:{},equipmentAge:{},
  potentialCaps:null,candidate:null,selectedRace:null,currentRaceWeather:null,injury:null,soundness:550,lastRaceAdvice:"",lastBreedingPartner:null
};

// Ver.0相当：単一キー時代の最小限セーブ。新項目がなくても保持して補完できること。
const legacy={horseName:"レトロスター",week:73,speed:612,stamina:580,prize:3210,races:8,wins:2,candidate:{coat:"栗毛"}};
const migrated=migrateSaveData(JSON.parse(JSON.stringify(legacy)),defaults);
assert.equal(migrated.fromVersion,0);
assert.equal(migrated.data.saveVersion,SCHEMA_VERSION);
assert.equal(migrated.data.horseName,"レトロスター");
assert.equal(migrated.data.week,79);
assert.equal(migrated.data.speed,612);
assert.equal(migrated.data.soundness,550);
assert.equal(migrated.data.lastBreedingPartner,null);
assert.deepEqual(migrated.data.raceHistory,[]);
assert.deepEqual(migrated.data.equipmentDurability,{});
assert.equal(migrated.data.candidate.sex,"牡馬");

// 途中版相当：追加フィールドがnullでも、利用時に例外になる型を残さないこと。
const malformed={...legacy,equipment:null,raceHistory:null,priorityRights:null,equipmentDurability:null,candidate:null};
const repaired=migrateSaveData(malformed,defaults).data;
assert.ok(Array.isArray(repaired.equipment));
assert.ok(Array.isArray(repaired.raceHistory));
assert.ok(Array.isArray(repaired.priorityRights));
assert.deepEqual(repaired.equipmentDurability,{});
assert.equal(repaired.candidate,null);

// 現行版の往復で主要データが変わらないこと。
const current={...defaults,horseName:"ドットキング",week:145,equipment:["pool"],equipmentDurability:{pool:64},raceHistory:[{raceName:"日本ダービー",place:1}]};
const roundTrip=migrateSaveData(JSON.parse(JSON.stringify(current)),defaults).data;
assert.deepEqual(roundTrip,current);

// v2の予約週と通常番組IDも、48週制から52週制へ同時に移行すること。
const oldReservation={...defaults,saveVersion:2,week:25,lastRaceWeek:24,reservedRaceId:"p-30-東京-11",reservationNotifiedId:"p-30-東京-11",selectedRace:{id:"p-30-東京-11",week:30,name:"予約戦"}};
const converted=migrateSaveData(oldReservation,defaults).data;
assert.equal(converted.week,27);
assert.equal(converted.lastRaceWeek,26);
assert.equal(converted.selectedRace.week,32);
assert.equal(converted.selectedRace.id,"p-32-東京-11");
assert.equal(converted.reservedRaceId,"p-32-東京-11");
assert.equal(converted.reservationNotifiedId,"p-32-東京-11");

// 旧単一キーからスロット1へ実データ文字列をコピーし、旧キーを消さないこと。
class MemoryStorage{
  constructor(entries={}){this.values=new Map(Object.entries(entries));this.removed=[];this.clearCount=0}
  getItem(key){return this.values.has(key)?this.values.get(key):null}
  setItem(key,value){this.values.set(key,String(value))}
  removeItem(key){this.removed.push(key);this.values.delete(key)}
  clear(){this.clearCount++;this.values.clear()}
}
const legacyRaw=JSON.stringify(legacy),storage=new MemoryStorage({dotKeibaTrialV3:legacyRaw});
assert.equal(copyLegacySave(storage,"dotKeibaTrialV3","dotKeibaTrialV3Slot",3),true);
assert.equal(storage.getItem("dotKeibaTrialV3Slot1"),legacyRaw);
assert.equal(storage.getItem("dotKeibaTrialV3"),legacyRaw);
assert.deepEqual(storage.removed,[]);
assert.equal(storage.clearCount,0);

// 保存キーを維持し、無条件clearや旧キー削除がないことを静的にも確認。
const appSource=fs.readFileSync(path.join(__dirname,"..","app.js"),"utf8");
assert.match(appSource,/const LEGACY_SAVE_KEY = "dotKeibaTrialV3"/);
assert.match(appSource,/const SAVE_KEY_PREFIX = "dotKeibaTrialV3Slot"/);
assert.doesNotMatch(appSource,/localStorage\.clear\s*\(/);
assert.doesNotMatch(appSource,/removeItem\(LEGACY_SAVE_KEY\)/);

console.log(`save compatibility: OK (schema v${SCHEMA_VERSION})`);

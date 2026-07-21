(function(root,factory){
  const api=factory();
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.DotKeibaSaveCompat=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  "use strict";
  const SCHEMA_VERSION=4;
  const ARRAY_FIELDS=[
    "equipment","priorityRights","raceHistory","favoriteRaces","galleryUnlocks","gradedTrophies",
    "tackUnlocked","declinedOverseasInvites","lineage","retirementRecords","raceReservations","overseasReservations","reservationNotifiedIds"
  ];
  const OBJECT_FIELDS=["equipmentDurability","equipmentAge"];

  function clone(value){
    if(Array.isArray(value))return value.map(clone);
    if(value&&typeof value==="object")return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,clone(item)]));
    return value;
  }

  function migrateSaveData(saved,defaults){
    if(!saved||typeof saved!=="object"||Array.isArray(saved))throw new TypeError("invalid save data");
    const fromVersion=Number.isInteger(saved.saveVersion)&&saved.saveVersion>=0?saved.saveVersion:0;
    const data={...clone(defaults),...clone(saved),saveVersion:SCHEMA_VERSION};
    ARRAY_FIELDS.forEach(field=>{
      data[field]=Array.isArray(saved[field])?clone(saved[field]):clone(defaults[field]||[]);
    });
    OBJECT_FIELDS.forEach(field=>{
      data[field]=saved[field]&&typeof saved[field]==="object"&&!Array.isArray(saved[field])?clone(saved[field]):clone(defaults[field]||{});
    });
    if(saved.potentialCaps&&typeof saved.potentialCaps==="object"&&!Array.isArray(saved.potentialCaps))data.potentialCaps=clone(saved.potentialCaps);
    else data.potentialCaps=null;
    if(saved.candidate&&typeof saved.candidate==="object"&&!Array.isArray(saved.candidate)){
      data.candidate=clone(saved.candidate);
      if(!data.candidate.sex)data.candidate.sex="牡馬";
    }else data.candidate=null;
    if(saved.selectedRace&&typeof saved.selectedRace==="object"&&!Array.isArray(saved.selectedRace))data.selectedRace=clone(saved.selectedRace);
    else data.selectedRace=null;
    if(saved.currentRaceWeather&&typeof saved.currentRaceWeather==="object"&&!Array.isArray(saved.currentRaceWeather))data.currentRaceWeather=clone(saved.currentRaceWeather);
    else data.currentRaceWeather=null;
    if(saved.injury&&typeof saved.injury==="object"&&!Array.isArray(saved.injury))data.injury=clone(saved.injury);
    else data.injury=null;
    // v2までは1年48週（月4週固定）。年数と季節を保ったまま52週制へ移す。
    if(fromVersion<3){
      const to52=week=>{
        if(!Number.isFinite(week)||week<1)return week;
        const oldYear=Math.floor((week-1)/48),oldWeek=(week-1)%48;
        return oldYear*52+Math.round(oldWeek*51/47)+1;
      };
      const programIdTo52=id=>typeof id==="string"?id.replace(/^(p-|supplement-)(\d+)-/,(_,prefix,week)=>`${prefix}${to52(Number(week))}-`):id;
      data.week=to52(data.week)||1;
      data.lastRaceWeek=to52(data.lastRaceWeek);
      data.reservedRaceId=programIdTo52(data.reservedRaceId);
      data.reservationNotifiedId=programIdTo52(data.reservationNotifiedId);
      if(data.selectedRace&&Number.isFinite(data.selectedRace.week)){
        const oldWeek=data.selectedRace.week,newWeek=to52(oldWeek);
        data.selectedRace.week=newWeek;
        if(typeof data.selectedRace.id==="string"&&data.selectedRace.id.startsWith(`p-${oldWeek}-`))data.selectedRace.id=data.selectedRace.id.replace(`p-${oldWeek}-`,`p-${newWeek}-`);
      }
      data.raceHistory=data.raceHistory.map(item=>Number.isFinite(item?.week)?{...item,week:to52(item.week)}:item);
    }
    // v3までは国内・海外共通の単一予約。通常予約と海外招待予約へ分離する。
    if(fromVersion<4&&data.reservedRaceId){
      const target=String(data.reservedRaceId).startsWith("overseas-")?data.overseasReservations:data.raceReservations;
      if(!target.includes(data.reservedRaceId))target.push(data.reservedRaceId);
    }
    if(fromVersion<4&&data.reservationNotifiedId&&!data.reservationNotifiedIds.includes(data.reservationNotifiedId))data.reservationNotifiedIds.push(data.reservationNotifiedId);
    data.reservedRaceId=null;data.reservationNotifiedId=null;
    return {data,fromVersion,changed:JSON.stringify(data)!==JSON.stringify(saved)};
  }

  function copyLegacySave(storage,legacyKey,slotPrefix,slotCount=3){
    const legacyRaw=storage.getItem(legacyKey);
    if(!legacyRaw)return false;
    const hasSlot=Array.from({length:slotCount},(_,index)=>index+1).some(slot=>storage.getItem(`${slotPrefix}${slot}`));
    if(hasSlot)return false;
    storage.setItem(`${slotPrefix}1`,legacyRaw);
    return true;
  }

  return {SCHEMA_VERSION,migrateSaveData,copyLegacySave};
});

(function(root,factory){
  const api=factory();
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.DotKeibaSaveCompat=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  "use strict";
  const SCHEMA_VERSION=2;
  const ARRAY_FIELDS=[
    "equipment","priorityRights","raceHistory","favoriteRaces","galleryUnlocks","gradedTrophies",
    "tackUnlocked","declinedOverseasInvites","lineage","retirementRecords"
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

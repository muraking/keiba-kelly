// JRA公式コース紹介・地方競馬全国協会「コース一覧」の上面図と諸元を、
// ゲーム用の正規化中心線座標へ再構成したデータ。公式画像そのものは使用しない。
// path はホーム直線の入口から進行方向に1周する座標（Canvas論理座標 360x500）。
(function(){
  const P={
    sapporo:[[48,62],[156,49],[290,58],[329,87],[337,166],[311,222],[232,244],[104,240],[48,211],[30,151],[32,92]],
    hakodate:[[52,61],[164,50],[286,60],[326,91],[333,164],[305,220],[224,240],[103,237],[47,207],[29,148],[33,91]],
    fukushima:[[47,61],[151,52],[286,61],[326,94],[330,169],[300,222],[218,241],[99,236],[43,204],[30,143],[34,91]],
    niigata:[[33,60],[133,52],[300,58],[337,86],[342,168],[314,224],[235,246],[89,240],[28,205],[17,143],[21,91]],
    tokyo:[[31,61],[137,50],[300,57],[339,87],[342,170],[310,224],[225,246],[86,239],[25,202],[18,140],[22,90]],
    nakayamaOuter:[[43,62],[145,52],[287,58],[327,86],[337,157],[310,219],[237,242],[104,239],[43,207],[27,148],[31,93]],
    nakayamaInner:[[54,63],[151,55],[279,61],[316,90],[321,164],[292,211],[218,230],[111,228],[55,201],[39,149],[43,96]],
    chukyo:[[37,61],[143,52],[293,58],[332,89],[337,165],[305,220],[224,244],[91,238],[34,205],[22,143],[26,92]],
    kyotoOuter:[[37,61],[135,53],[294,57],[334,89],[337,166],[303,222],[218,245],[86,238],[31,202],[21,141],[25,91]],
    kyotoInner:[[49,62],[146,56],[282,61],[319,91],[323,164],[293,212],[216,231],[105,227],[49,198],[36,147],[40,96]],
    hanshinOuter:[[34,61],[142,52],[301,58],[338,91],[339,167],[306,222],[218,245],[83,237],[27,200],[20,139],[24,91]],
    hanshinInner:[[49,62],[150,55],[282,61],[318,92],[321,165],[292,212],[216,232],[105,228],[49,200],[36,148],[40,96]],
    kokura:[[49,62],[153,54],[286,61],[326,93],[329,167],[299,218],[219,238],[103,234],[47,203],[33,147],[37,94]],
    monbetsuOuter:[[34,62],[140,51],[298,59],[337,91],[340,168],[307,225],[219,247],[82,239],[25,201],[20,138],[24,90]],
    monbetsuInner:[[52,63],[151,56],[280,62],[317,92],[320,164],[291,211],[216,231],[108,228],[52,201],[39,149],[43,96]],
    moriokaDirt:[[31,62],[139,51],[299,59],[338,92],[340,169],[305,225],[216,247],[78,238],[22,199],[18,138],[23,90]],
    moriokaTurf:[[49,64],[151,56],[281,62],[318,93],[321,165],[289,212],[211,231],[103,227],[48,197],[36,147],[41,97]],
    mizusawa:[[53,63],[154,56],[280,63],[315,94],[318,166],[288,210],[213,228],[108,226],[54,199],[42,149],[46,98]],
    urawa:[[58,63],[153,58],[276,63],[311,94],[314,165],[286,207],[214,225],[113,224],[59,199],[47,150],[50,99]],
    funabashiOuter:[[42,62],[146,53],[291,60],[330,91],[333,168],[301,219],[219,241],[94,236],[39,203],[28,145],[32,93]],
    funabashiInner:[[56,64],[153,58],[276,64],[311,94],[314,164],[285,207],[213,225],[113,223],[58,198],[47,151],[50,100]],
    oiOuter:[[32,62],[139,51],[299,59],[339,91],[341,170],[307,226],[219,248],[79,239],[22,200],[18,138],[23,90]],
    oiInner:[[49,63],[150,56],[283,62],[319,93],[322,166],[291,213],[214,232],[104,228],[49,198],[36,147],[41,97]],
    kawasaki:[[55,63],[153,57],[278,64],[313,95],[316,166],[286,209],[213,227],[111,225],[56,199],[44,150],[48,99]],
    kanazawa:[[52,63],[150,56],[281,63],[317,94],[320,166],[291,211],[216,230],[106,227],[51,200],[38,148],[42,97]],
    kasamatsu:[[61,64],[157,59],[273,65],[307,96],[310,163],[283,204],[212,222],[119,222],[64,200],[51,153],[54,101]],
    nagoya:[[57,63],[153,57],[277,64],[312,95],[316,165],[286,208],[211,226],[112,224],[58,199],[46,151],[50,100]],
    sonoda:[[64,64],[157,60],[270,66],[303,96],[306,162],[280,202],[211,220],[122,220],[67,199],[55,154],[57,103]],
    himeji:[[56,63],[153,57],[278,64],[313,95],[316,165],[286,209],[212,227],[111,225],[57,199],[44,151],[48,100]],
    kochi:[[65,64],[158,60],[269,67],[301,98],[304,159],[278,201],[207,221],[119,220],[63,197],[52,153],[56,104]],
    saga:[[62,64],[157,59],[271,66],[304,97],[307,161],[280,203],[210,222],[119,221],[64,198],[52,153],[55,103]]
  };
  const distances={
    jraTurf:[1000,1200,1400,1500,1600,1700,1800,2000,2200,2400,2500,2600,3000,3200,3400,3600],
    jraDirt:[1000,1150,1200,1300,1400,1600,1700,1800,1900,2000,2100,2400,2500],
    local:[800,900,920,1000,1100,1200,1230,1300,1400,1500,1600,1700,1800,1900,2000,2100,2400,2500]
  };
  const c=(id,name,category,direction,surfaces,layouts,meta)=>({id,name,category,direction,surfaces,layouts,...meta});
  const D={
    "札幌":c("sapporo","札幌競馬場","JRA","right",["turf","dirt"],{turf:P.sapporo,dirt:P.sapporo},{lap:{turf:1640.9,dirt:1487},straight:{turf:266.1,dirt:264.3},elevation:.7,width:"20-30m",corner:"丸みの強い大コーナー",spiral:false,slopes:[],distances}),
    "函館":c("hakodate","函館競馬場","JRA","right",["turf","dirt"],{turf:P.hakodate,dirt:P.hakodate},{lap:{turf:1626.6,dirt:1475.8},straight:{turf:262.1,dirt:260.3},elevation:3.5,width:"20-29m",corner:"小回り",spiral:false,slopes:["3角から4角へ下り"],distances}),
    "福島":c("fukushima","福島競馬場","JRA","right",["turf","dirt"],{turf:P.fukushima,dirt:P.fukushima},{lap:{turf:1600,dirt:1444.6},straight:{turf:292,dirt:295.7},elevation:1.9,width:"20-27m",corner:"小回り",spiral:true,slopes:["向正面上り","4角から直線下り"],distances}),
    "新潟":c("niigata","新潟競馬場","JRA","left",["turf","dirt"],{turf_outer:P.niigata,turf_inner:P.fukushima,dirt:P.niigata,straight:[[18,150],[342,150]]},{lap:{turf_outer:2223,turf_inner:1623,dirt:1472.5},straight:{turf_outer:658.7,turf_inner:358.7,dirt:353.9},elevation:2.2,width:"25m",corner:"外回りは大きく緩い",spiral:true,slopes:["外回り3角付近に緩い起伏"],distances}),
    "東京":c("tokyo","東京競馬場","JRA","left",["turf","dirt"],{turf:P.tokyo,dirt:P.tokyo},{lap:{turf:2083.1,dirt:1899},straight:{turf:525.9,dirt:501.6},elevation:2.7,width:"25-41m",corner:"大きく緩い",spiral:false,slopes:["向正面下り","直線残り460m付近から上り"],distances}),
    "中山":c("nakayama","中山競馬場","JRA","right",["turf","dirt"],{turf_outer:P.nakayamaOuter,turf_inner:P.nakayamaInner,dirt:P.nakayamaInner},{lap:{turf_outer:1839.7,turf_inner:1667.1,dirt:1493},straight:{turf:310,dirt:308},elevation:5.3,width:"20-32m",corner:"内回りはタイト",spiral:false,slopes:["ゴール前急坂"],distances}),
    "中京":c("chukyo","中京競馬場","JRA","left",["turf","dirt"],{turf:P.chukyo,dirt:P.chukyo},{lap:{turf:1705.9,dirt:1530},straight:{turf:412.5,dirt:410.7},elevation:3.5,width:"25-30m",corner:"3・4角スパイラル",spiral:true,slopes:["直線入口に急坂"],distances}),
    "京都":c("kyoto","京都競馬場","JRA","right",["turf","dirt"],{turf_outer:P.kyotoOuter,turf_inner:P.kyotoInner,dirt:P.kyotoInner},{lap:{turf_outer:1894.3,turf_inner:1782.8,dirt:1607.6},straight:{turf_outer:403.7,turf_inner:328.4,dirt:329.1},elevation:4.3,width:"28-38m",corner:"内回りはタイト",spiral:false,slopes:["3角の丘"],distances}),
    "阪神":c("hanshin","阪神競馬場","JRA","right",["turf","dirt"],{turf_outer:P.hanshinOuter,turf_inner:P.hanshinInner,dirt:P.hanshinInner},{lap:{turf_outer:2089,turf_inner:1689,dirt:1517.6},straight:{turf_outer:473.6,turf_inner:356.5,dirt:352.7},elevation:2.4,width:"24-28m",corner:"外回りは大きく緩い",spiral:false,slopes:["ゴール前急坂"],distances}),
    "小倉":c("kokura","小倉競馬場","JRA","right",["turf","dirt"],{turf:P.kokura,dirt:P.kokura},{lap:{turf:1615.1,dirt:1445.4},straight:{turf:293,dirt:291.3},elevation:3,width:"24-30m",corner:"小回り",spiral:true,slopes:["2角付近最高点から下り"],distances}),
    "帯広":c("obihiro","帯広競馬場","LOCAL","straight",["banei"],{banei:[[20,160],[340,160]]},{lap:{banei:200},straight:{banei:200},elevation:1.6,width:"21m",corner:"なし",spiral:false,slopes:["第1障害1.0m","第2障害1.6m"],distances:{banei:[200]},fullGate:10,obstacles:[{at:.35,height:1},{at:.68,height:1.6}]}),
    "門別":c("monbetsu","門別競馬場","LOCAL","right",["dirt"],{dirt_outer:P.monbetsuOuter,dirt_inner:P.monbetsuInner},{lap:{dirt_outer:1600,dirt_inner:1376},straight:{dirt_outer:330,dirt_inner:218},elevation:1.54,width:"25m",corner:"外回りは緩い",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:16}),
    "盛岡":c("morioka","盛岡競馬場","LOCAL","left",["turf","dirt"],{turf:P.moriokaTurf,dirt:P.moriokaDirt},{lap:{turf:1400,dirt:1600},straight:{turf:300,dirt:300},elevation:4.6,width:"25m",corner:"大きい",spiral:false,slopes:["全周に起伏"],distances:{turf:distances.local,dirt:distances.local},fullGate:16}),
    "水沢":c("mizusawa","水沢競馬場","LOCAL","right",["dirt"],{dirt:P.mizusawa},{lap:{dirt:1200},straight:{dirt:245},elevation:0,width:"20m",corner:"小回り",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:12}),
    "浦和":c("urawa","浦和競馬場","LOCAL","left",["dirt"],{dirt:P.urawa},{lap:{dirt:1200},straight:{dirt:220},elevation:0,width:"16-21.5m",corner:"タイト",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:14}),
    "船橋":c("funabashi","船橋競馬場","LOCAL","left",["dirt"],{dirt_outer:P.funabashiOuter,dirt_inner:P.funabashiInner},{lap:{dirt_outer:1400,dirt_inner:1250},straight:{dirt:308},elevation:0,width:"20-25m",corner:"内外回り",spiral:true,slopes:[],distances:{dirt:distances.local},fullGate:14}),
    "大井":c("oi","大井競馬場","LOCAL","both",["dirt"],{dirt_outer:P.oiOuter,dirt_inner:P.oiInner},{lap:{dirt_outer:1600,dirt_inner:1400},straight:{dirt_outer_right:386,dirt_outer_left:300,dirt_inner:286},elevation:0,width:"25m",corner:"外回り大、内回り小",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:16}),
    "川崎":c("kawasaki","川崎競馬場","LOCAL","left",["dirt"],{dirt:P.kawasaki},{lap:{dirt:1200},straight:{dirt:300},elevation:0,width:"25m",corner:"タイト",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:14}),
    "金沢":c("kanazawa","金沢競馬場","LOCAL","right",["dirt"],{dirt:P.kanazawa},{lap:{dirt:1200},straight:{dirt:236},elevation:0,width:"20m",corner:"4コーナー全てにポケット",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:12}),
    "笠松":c("kasamatsu","笠松競馬場","LOCAL","right",["dirt"],{dirt:P.kasamatsu},{lap:{dirt:1100},straight:{dirt:201},elevation:1.92,width:"20m",corner:"小回り",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:12}),
    "名古屋":c("nagoya","名古屋競馬場","LOCAL","right",["dirt"],{dirt:P.nagoya},{lap:{dirt:1180},straight:{dirt:240},elevation:0,width:"30m",corner:"3・4角スパイラル",spiral:true,slopes:[],distances:{dirt:distances.local},fullGate:12}),
    "園田":c("sonoda","園田競馬場","LOCAL","right",["dirt"],{dirt:P.sonoda},{lap:{dirt:1051},straight:{dirt:213},elevation:1.23,width:"20-24m",corner:"極小回り",spiral:false,slopes:["向正面から3角へ上り"],distances:{dirt:distances.local},fullGate:12}),
    "姫路":c("himeji","姫路競馬場","LOCAL","right",["dirt"],{dirt:P.himeji},{lap:{dirt:1200},straight:{dirt:230},elevation:0,width:"20-25m",corner:"小回り",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:12}),
    "高知":c("kochi","高知競馬場","LOCAL","right",["dirt"],{dirt:P.kochi},{lap:{dirt:1100},straight:{dirt:200},elevation:1.58,width:"22-27m",corner:"1・2角が3・4角より小さい",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:12}),
    "佐賀":c("saga","佐賀競馬場","LOCAL","right",["dirt"],{dirt:P.saga},{lap:{dirt:1100},straight:{dirt:200},elevation:1,width:"19.2-24m",corner:"小回り",spiral:false,slopes:[],distances:{dirt:distances.local},fullGate:12})
  };
  const pointAt=(path,p)=>{
    if(path.length===2)return{x:path[0][0]+(path[1][0]-path[0][0])*p,y:path[0][1]+(path[1][1]-path[0][1])*p};
    const lengths=path.map((a,i)=>{const b=path[(i+1)%path.length];return Math.hypot(b[0]-a[0],b[1]-a[1])});
    const total=lengths.reduce((a,b)=>a+b,0);let target=((p%1)+1)%1*total;
    for(let i=0;i<path.length;i++){if(target<=lengths[i]){const a=path[i],b=path[(i+1)%path.length],t=target/lengths[i];return{x:a[0]+(b[0]-a[0])*t,y:a[1]+(b[1]-a[1])*t}}target-=lengths[i]}
    return{x:path[0][0],y:path[0][1]};
  };
  Object.values(D).forEach(course=>{
    course.finishProgress=course.direction==="straight"?1:.15;
    const primaryKey=Object.keys(course.layouts)[0],primaryPath=course.layouts[primaryKey];
    course.finishLine=pointAt(primaryPath,course.finishProgress);
    course.startPositions={};
    Object.entries(course.layouts).forEach(([layout,path])=>{
      const surface=layout.startsWith("turf")?"turf":layout.startsWith("banei")?"banei":"dirt";
      const lap=course.lap[layout]||course.lap[surface]||Object.values(course.lap)[0];
      const available=course.distances[surface]||course.distances[surface==="turf"?"jraTurf":surface==="dirt"?"jraDirt":"banei"]||[];
      available.forEach(distance=>{
        const finishLogical=course.direction==="right"?1-course.finishProgress:course.finishProgress;
        const progress=course.direction==="straight"?0:((finishLogical-distance/lap)%1+1)%1;
        const rendered=course.direction==="right"?(1-progress)%1:progress;
        course.startPositions[`${layout}_${distance}`]={...pointAt(path,rendered),progress};
      });
    });
  });
  window.COURSE_LAYOUTS=D;
})();

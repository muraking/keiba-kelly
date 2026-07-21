const fs=require("fs");
const path=require("path");
const root=path.resolve(__dirname,"..");
const race=fs.readFileSync(path.join(root,"race.js"),"utf8");
const app=fs.readFileSync(path.join(root,"app.js"),"utf8");
const html=fs.readFileSync(path.join(root,"index.html"),"utf8");

function ok(condition,message){if(!condition)throw new Error(message)}

ok(race.includes("finishDisplayMargins.size===0&&horses.some(h=>h.finished)"),"先頭馬のゴール時点で写真判定距離を保存していません");
ok(race.includes("Math.hypot(front.x-back.x,front.y-back.y)/14"),"着差が画面上の馬体間隔を使用していません");
ok(race.includes("finishDisplayMargins.set(snapshotOrder[i].id"),"ゴール時の画面上の着差を保存していません");
ok(!race.includes("Number.isFinite(visualLengths)?visualLengths"),"駆け抜け後の画面座標が着差へ残っています");
ok(race.includes('"メイダン":{turn:"左"'),"メイダンの回り方向が未設定です");
ok(race.includes('"パリロンシャン":{turn:"右"'),"パリロンシャンの回り方向が未設定です");
ok(race.includes('"シャティン":{turn:"右"'),"シャティンの回り方向が未設定です");
ok(app.includes("horseAppearance:{color:"),"トロフィーに優勝時の馬体情報を保存していません");
ok(app.includes("const appearance=trophy.horseAppearance||currentHorseAppearance"),"トロフィー表示が保存時の馬体情報を使用していません");
ok(app.includes("const arrived=r.week===game.week,debutSeasonOpen=r.week>=23"),"未来の新馬開始週で予約可否を判定していません");
ok(!html.includes("raceReservableOnly"),"意味の重複する予約可能のみフィルターが残っています");
console.log("Race finish, trophy, overseas course and booking checks passed.");

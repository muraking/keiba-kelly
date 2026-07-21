const fs=require("fs"),path=require("path"),root=path.resolve(__dirname,"..");
const app=fs.readFileSync(path.join(root,"app.js"),"utf8"),race=fs.readFileSync(path.join(root,"race.js"),"utf8"),css=fs.readFileSync(path.join(root,"style.css"),"utf8");
function ok(value,message){if(!value)throw new Error(message)}
ok(app.includes('const whiteChance=parentCoat==="白毛"?.08:.0015'),"白毛の通常・遺伝確率が未設定です");
ok(app.includes("faceMarkType,legMarks"),"顔白斑と四肢白が外見DNAにありません");
ok(app.includes('maneStyle:inherit("maneStyle")'),"たてがみの遺伝がありません");
ok(app.includes('tailStyle:inherit("tailStyle")'),"尻尾の遺伝がありません");
ok(app.includes("normalizeAppearanceDNA(game.candidate)"),"既存セーブの外見DNA補完が呼ばれていません");
ok(race.includes("randomOpponentAppearance"),"対戦馬ごとの外見生成がありません");
ok(race.includes("playerSetup.appearance"),"愛馬の外見がレースへ渡っていません");
ok(app.includes("function renderAppearanceTest()"),"開発者用の見た目サンプル画面がありません");
ok(app.includes("appearanceSampleVariants"),"組み合わせサンプルが生成されていません");
["face-star","face-doubleBlaze","face-snip","face-starSnip","mane-wavy","tail-long","front-sock-2","back-sock-2"].forEach(name=>ok(css.includes(`.${name}`),`${name}の描画がありません`));
console.log("horse appearance DNA: OK");

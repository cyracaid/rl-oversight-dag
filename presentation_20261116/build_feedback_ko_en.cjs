const fs = require('fs');
const path = require('path');
const {Document,Packer,Paragraph,TextRun,HeadingLevel,Footer,PageNumber} = require('/private/var/folders/rw/0p5p9d812dbgk7qw_mxpcfz40000gn/T/opencode/team6-docx/node_modules/docx');
const stem = path.join(__dirname,'Team6_v3_4_2_Feedback_KO_EN');
const children = fs.readFileSync(stem+'.md','utf8').split(/\n\s*\n/).filter(Boolean).map(block=>{
  const h=block.match(/^(#{1,3}) (.*)$/);
  return new Paragraph({...(h?{heading:[HeadingLevel.TITLE,HeadingLevel.HEADING_1,HeadingLevel.HEADING_2][h[1].length-1]}:{}),spacing:{after:120,line:280},children:[new TextRun(block.replace(/^#{1,3} /,'').replace(/\n/g,' '))]});
});
const doc=new Document({title:'6조 v3_4_2 대본 최종 피드백',styles:{default:{document:{run:{font:{ascii:'Arial',eastAsia:'맑은 고딕',hAnsi:'Arial'},size:21}}}},sections:[{properties:{page:{size:{width:11906,height:16838},margin:{top:1080,bottom:1080,left:1134,right:1134}}},footers:{default:new Footer({children:[new Paragraph({children:[new TextRun('Team 6 | v3_4_2 | '),new TextRun({children:[PageNumber.CURRENT]})]})]})},children}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync(stem+'.docx',b);console.log(stem+'.docx');});

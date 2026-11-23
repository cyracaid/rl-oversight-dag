const fs = require('fs');
const path = require('path');
const {Document,Packer,Paragraph,TextRun,HeadingLevel,Footer,PageNumber} = require('/private/var/folders/rw/0p5p9d812dbgk7qw_mxpcfz40000gn/T/opencode/team6-docx/node_modules/docx');
const stem = path.join(__dirname,'Team6_v3_4_2_Final_Review');
const content = fs.readFileSync(stem+'.md','utf8');
const children = content.split(/\n\s*\n/).filter(Boolean).map(block=>{
  const h = block.match(/^(#{1,3}) (.*)$/);
  if(h) return new Paragraph({heading: h[1].length===1?HeadingLevel.TITLE:h[1].length===2?HeadingLevel.HEADING_1:HeadingLevel.HEADING_2,
    pageBreakBefore: h[2].startsWith('3. 英文')||h[2].startsWith('4. 英文'),
    children:[new TextRun(h[2])]});
  return new Paragraph({spacing:{after:140,line:300},children:[new TextRun(block.replace(/\n/g,' '))]});
});
const doc = new Document({creator:'Team 6',title:'Team 6 v3_4_2 Final Script Review',
 styles:{default:{document:{run:{font:'Arial',size:22}}},paragraphStyles:[
  {id:'Heading1',name:'Heading 1',basedOn:'Normal',next:'Normal',quickFormat:true,run:{font:'Arial',size:30,bold:true,color:'182C29'},paragraph:{outlineLevel:0,spacing:{before:260,after:160},keepNext:true}},
  {id:'Heading2',name:'Heading 2',basedOn:'Normal',next:'Normal',quickFormat:true,run:{font:'Arial',size:25,bold:true,color:'267663'},paragraph:{outlineLevel:1,spacing:{before:200,after:100},keepNext:true}}
 ]},sections:[{properties:{page:{size:{width:11906,height:16838},margin:{top:1134,bottom:1134,left:1134,right:1134}}},
 footers:{default:new Footer({children:[new Paragraph({children:[new TextRun('Team 6 | v3_4_2 | '),new TextRun({children:[PageNumber.CURRENT]})]})]})},children}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync(stem+'.docx',b);console.log(stem+'.docx');});

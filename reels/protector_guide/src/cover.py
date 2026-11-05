import subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
from fx import *
src = "/root/.claude/uploads/4d0dac7b-7b1e-524e-acb0-cc9ba3078324/95b265ae-IMG_5872.mov"
raw = subprocess.run(["ffmpeg","-v","error","-ss","4.6","-i",src,"-frames:v","1","-vf",
  "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=saturation=1.2:brightness=0.03",
  "-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True).stdout
img = Image.frombytes("RGB",(W,H),raw).convert("RGBA")
def blob(x0,y0,x1,y1,col,rot):
    s=Image.new("RGBA",(x1-x0+40,y1-y0+40),(0,0,0,0)); d=ImageDraw.Draw(s)
    d.rounded_rectangle([20,20,x1-x0+20,y1-y0+20],radius=60,fill=col)
    s=s.rotate(rot,Image.BICUBIC,expand=True)
    img.alpha_composite(s,(int((x0+x1)/2-s.width/2),int((y0+y1)/2-s.height/2)))
blob(160,250,920,470,CREAM+(240,),2)
blob(70,470,1010,700,CREAM+(240,),-1.5)
blob(180,690,900,930,CREAM+(240,),1)
blob(150,960,930,1110,MINT+(245,),0)
draw_text_block(img,[L:=None] and [] or [dict(segs=[("子どもの",BROWN)],size=130,marker=YELLOW)],9,0,W/2,cy_top=270,maxw=720)
draw_text_block(img,[dict(segs=[("プロテクター",ORANGE)],size=140,marker=YELLOW)],9,0,W/2,cy_top=495,maxw=900)
draw_text_block(img,[dict(segs=[("選び方！",CORAL)],size=170)],9,0,W/2,cy_top=705,maxw=700)
draw_text_block(img,[dict(segs=[("ミニランプで転んでも安心",BROWN)],size=64)],9,0,W/2,cy_top=985,maxw=740)
d=ImageDraw.Draw(img)
star(d,110,980,45,9); star(d,980,760,40,9)
burst(d,W/2,600,500,560,[190,200,210,-10,-20,-30],14,YELLOW)
# speech bubble
d.ellipse([640,1180,1000,1400],fill=CREAM,outline=BROWN,width=6)
d.polygon([(700,1370),(660,1450),(760,1390)],fill=CREAM)
d.text((820,1290),"買う場所も\n紹介！",font=font(POP,50),fill=BROWN,anchor="mm",align="center")
img.convert("RGB").save(sys.argv[1],quality=95)

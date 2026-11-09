#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass, field
from math import inf
from time import perf_counter
from typing import Optional
try:
 import tkinter as tk
 from tkinter import ttk,messagebox
except ImportError: tk=ttk=messagebox=None
N=8; EMPTY,BLACK,WHITE=0,1,-1
DIRS=((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1))
NAME={BLACK:"Чорні",WHITE:"Білі"}; WIN=1_000_000
@dataclass(frozen=True)
class Move:
 sr:int; sc:int; er:int; ec:int
 def notation(self):
  q=lambda r,c:f"{chr(97+c)}{N-r}"
  return f"{q(self.sr,self.sc)}-{q(self.er,self.ec)}"
@dataclass(frozen=True)
class State:
 board:tuple[tuple[int,...],...]; turn:int=BLACK; last:int=EMPTY; ply:int=0
 @staticmethod
 def initial():
  b=[[0]*N for _ in range(N)]
  for c in range(1,N-1): b[0][c]=b[N-1][c]=BLACK
  for r in range(1,N-1): b[r][0]=b[r][N-1]=WHITE
  return State(tuple(map(tuple,b)))
 @staticmethod
 def inside(r,c): return 0<=r<N and 0<=c<N
 def pieces(self,p): return [(r,c) for r in range(N) for c in range(N) if self.board[r][c]==p]
 def line_count(self,r,c,dr,dc):
  n=1
  rr,cc=r+dr,c+dc
  while self.inside(rr,cc): n+=self.board[rr][cc]!=0; rr+=dr; cc+=dc
  rr,cc=r-dr,c-dc
  while self.inside(rr,cc): n+=self.board[rr][cc]!=0; rr-=dr; cc-=dc
  return int(n)
 def moves(self,p=None):
  p=self.turn if p is None else p; enemy=-p; out=[]
  for r,c in self.pieces(p):
   for dr,dc in DIRS:
    d=self.line_count(r,c,dr,dc); er,ec=r+dr*d,c+dc*d
    if not self.inside(er,ec) or self.board[er][ec]==p: continue
    if any(self.board[r+dr*k][c+dc*k]==enemy for k in range(1,d)): continue
    out.append(Move(r,c,er,ec))
  return out
 def play(self,m):
  b=[list(x) for x in self.board]; b[m.er][m.ec]=self.turn; b[m.sr][m.sc]=0
  return State(tuple(map(tuple,b)),-self.turn,self.turn,self.ply+1)
 def components(self,p):
  left=set(self.pieces(p)); sizes=[]
  while left:
   stack=[left.pop()]; size=1
   while stack:
    r,c=stack.pop()
    for dr,dc in DIRS:
     q=(r+dr,c+dc)
     if q in left: left.remove(q); stack.append(q); size+=1
   sizes.append(size)
  return sorted(sizes,reverse=True)
 def connected(self,p): return len(self.components(p))==1
 def winner(self):
  b,w=self.connected(BLACK),self.connected(WHITE)
  return self.last if b and w else BLACK if b else WHITE if w else EMPTY
@dataclass
class Stats:
 nodes:int=0; leaves:int=0; cutoffs:int=0; seconds:float=0.; trace:list[str]=field(default_factory=list)
@dataclass
class Result: move:Optional[Move]; score:float; stats:Stats
def compact(s,p):
 ps=s.pieces(p)
 if not ps:return -1000
 cr=sum(r for r,_ in ps)/len(ps); cc=sum(c for _,c in ps)/len(ps)
 return -sum((r-cr)**2+(c-cc)**2 for r,c in ps)/len(ps)
def centre(s,p): return sum(7-abs(r-3.5)-abs(c-3.5) for r,c in s.pieces(p))
def evaluate(s,maxp):
 w=s.winner()
 if w==maxp:return WIN-s.ply
 if w==-maxp:return -WIN+s.ply
 a,b=s.components(maxp),s.components(-maxp)
 return 120*((a[0] if a else 0)-(b[0] if b else 0))-45*(len(a)-len(b))+18*(len(s.pieces(maxp))-len(s.pieces(-maxp)))+2*(len(s.moves(maxp))-len(s.moves(-maxp)))+1.5*(centre(s,maxp)-centre(s,-maxp))+3*(compact(s,maxp)-compact(s,-maxp))
def ordered(s,moves,maxp):
 def key(m):
  child=s.play(m); mover=s.turn
  x=(10000 if child.winner()==mover else 0)+1000*(len(s.components(mover))-len(child.components(mover)))
  return x if mover==maxp else -x
 return sorted(moves,key=key,reverse=s.turn==maxp)
def search(state,depth,maxp,alpha_beta=True,sorting=True,trace=False):
 st=Stats(); started=perf_counter(); limit=180
 def log(x):
  if trace and len(st.trace)<limit: st.trace.append(x)
 def fmt(x): return "-inf" if x==-inf else "+inf" if x==inf else f"{x:.1f}"
 def rec(s,d,a,b,level):
  st.nodes+=1; moves=s.moves(); w=s.winner(); pad="  "*level
  if d==0 or w or not moves:
   st.leaves+=1; v=evaluate(s,maxp); log(f"{pad}лист: UF/HEF={v:.1f}"); return v,None
  if sorting:moves=ordered(s,moves,maxp)
  maximizing=s.turn==maxp; best=-inf if maximizing else inf; bm=None
  log(f"{pad}{'MAX' if maximizing else 'MIN'} d={d}, alpha={fmt(a)}, beta={fmt(b)}, ходів={len(moves)}")
  for i,m in enumerate(moves):
   v,_=rec(s.play(m),d-1,a,b,level+1)
   if (maximizing and v>best) or (not maximizing and v<best):best,bm=v,m
   if alpha_beta:
    if maximizing:a=max(a,best)
    else:b=min(b,best)
    log(f"{pad}{m.notation()}: v={v:.1f}, alpha={fmt(a)}, beta={fmt(b)}")
    if a>=b:
     st.cutoffs+=1; log(f"{pad}ВІДТИНАННЯ: alpha >= beta; відкинуто {len(moves)-i-1} ходів"); break
  return best,bm
 score,move=rec(state,depth,-inf,inf,0); st.seconds=perf_counter()-started
 if trace and len(st.trace)>=limit:st.trace.append("... журнал обмежено 180 записами ...")
 return Result(move,score,st)
class App:
 CELL=70; PAD=28
 def __init__(self,root):
  self.root=root; root.title("Lines of Action"); root.resizable(False,False)
  self.state=State.initial(); self.human=WHITE; self.ai=BLACK; self.selected=None; self.targets={}; self.busy=False
  self.depth=tk.IntVar(value=3); self.status=tk.StringVar(value="Чорні починають. Натисніть «Хід комп'ютера»."); self.info=tk.StringVar(value="")
  f=ttk.Frame(root,padding=10); f.pack(); side=self.CELL*N+self.PAD*2
  self.canvas=tk.Canvas(f,width=side,height=side,bg="#efe4c8",highlightthickness=0); self.canvas.grid(row=0,column=0,columnspan=5); self.canvas.bind("<Button-1>",self.click)
  for col,(text,cmd) in enumerate((("Нова гра",self.reset),("Хід комп'ютера",self.ai_move),("Експеримент",self.experiment))):ttk.Button(f,text=text,command=cmd).grid(row=1,column=col,padx=4,pady=8,sticky="ew")
  ttk.Label(f,text="Глибина:").grid(row=1,column=3,padx=(12,2)); ttk.Spinbox(f,from_=1,to=4,textvariable=self.depth,width=4,state="readonly").grid(row=1,column=4)
  ttk.Label(f,textvariable=self.status,font=("Segoe UI",11,"bold"),wraplength=side).grid(row=2,column=0,columnspan=5,sticky="w"); ttk.Label(f,textvariable=self.info,wraplength=side).grid(row=3,column=0,columnspan=5,sticky="w"); self.draw()
 def reset(self):self.state=State.initial();self.selected=None;self.targets={};self.status.set("Чорні починають. Натисніть «Хід комп'ютера».");self.info.set("");self.draw()
 def draw(self):
  self.canvas.delete("all");p=self.PAD
  for r in range(N):
   for c in range(N):
    x=p+c*self.CELL;y=p+r*self.CELL;self.canvas.create_rectangle(x,y,x+self.CELL,y+self.CELL,fill=("#d9b97e","#f2d9a7")[(r+c)%2],outline="#70542f")
    if (r,c) in self.targets:self.canvas.create_oval(x+26,y+26,x+44,y+44,fill="#3b9f43",outline="")
    q=self.state.board[r][c]
    if q:self.canvas.create_oval(x+8,y+8,x+self.CELL-8,y+self.CELL-8,fill="#222831" if q==BLACK else "#f5f5f2",outline="#333",width=3)
    if self.selected==(r,c):self.canvas.create_rectangle(x+3,y+3,x+self.CELL-3,y+self.CELL-3,outline="#e53935",width=4)
  for i in range(N):self.canvas.create_text(p+i*self.CELL+self.CELL/2,13,text=chr(97+i));self.canvas.create_text(13,p+i*self.CELL+self.CELL/2,text=str(N-i))
 def click(self,e):
  if self.busy or self.state.turn!=self.human or self.state.winner():return
  c=(e.x-self.PAD)//self.CELL;r=(e.y-self.PAD)//self.CELL
  if not State.inside(r,c):return
  if (r,c) in self.targets:self.state=self.state.play(self.targets[(r,c)]);self.selected=None;self.targets={};self.after();return
  if self.state.board[r][c]==self.human:self.selected=(r,c);self.targets={(m.er,m.ec):m for m in self.state.moves() if (m.sr,m.sc)==(r,c)}
  else:self.selected=None;self.targets={}
  self.draw()
 def after(self):
  self.draw();w=self.state.winner()
  if w:self.status.set(f"Перемогли {NAME[w]}!");messagebox.showinfo("Гру завершено",self.status.get())
  else:self.status.set(f"Хід: {NAME[self.state.turn]}")
 def ai_move(self):
  if self.busy or self.state.turn!=self.ai or self.state.winner():return
  self.busy=True;self.status.set("Комп'ютер аналізує позицію...");self.root.update_idletasks();d=int(self.depth.get());r=search(self.state,d,self.ai,True,True)
  if r.move:self.state=self.state.play(r.move);self.info.set(f"Хід {r.move.notation()} | оцінка {r.score:.1f} | вузлів {r.stats.nodes} | відтинань {r.stats.cutoffs} | {r.stats.seconds:.3f} с")
  self.busy=False;self.after()
 def show_log(self,lines):
  w=tk.Toplevel(self.root);w.title("Журнал Alpha-beta");t=tk.Text(w,width=95,height=30,wrap="none",font=("Consolas",9));y=ttk.Scrollbar(w,command=t.yview);t.configure(yscrollcommand=y.set);t.pack(side="left",fill="both",expand=True);y.pack(side="left",fill="y");t.insert("1.0","\n".join(lines));t.configure(state="disabled")
 def experiment(self):
  if self.busy or self.state.winner():return
  self.busy=True;self.status.set("Порівняння алгоритмів...");self.root.update_idletasks();d=int(self.depth.get());maxp=self.state.turn
  rows=[("Minimax",search(self.state,d,maxp,False,False)),("Alpha-beta",search(self.state,d,maxp,True,False)),("Alpha-beta + сортування",search(self.state,d,maxp,True,True,True))]
  w=tk.Toplevel(self.root);w.title("Експеримент");cols=("a","m","s","n","c","t");tree=ttk.Treeview(w,columns=cols,show="headings",height=3)
  for col,title,width in zip(cols,("Алгоритм","Хід","Оцінка","Вузли","Відтинання","Час, с"),(190,80,90,90,90,90)):tree.heading(col,text=title);tree.column(col,width=width,anchor="center")
  for label,r in rows:tree.insert("","end",values=(label,r.move.notation() if r.move else "-",f"{r.score:.1f}",r.stats.nodes,r.stats.cutoffs,f"{r.stats.seconds:.4f}"))
  ttk.Label(w,text=f"Глибина: {d}. MAX: {NAME[maxp]}",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=12,pady=(12,6));tree.pack(padx=12,pady=6)
  buttons=ttk.Frame(w);buttons.pack(pady=10);ttk.Button(buttons,text="Показати журнал Alpha-beta",command=lambda:self.show_log(rows[-1][1].stats.trace)).pack(side="left",padx=5);ttk.Button(buttons,text="Закрити",command=w.destroy).pack(side="left",padx=5)
  self.status.set(f"Хід: {NAME[self.state.turn]}");self.busy=False
def self_test():
 s=State.initial();assert len(s.pieces(BLACK))==12 and any(m.notation()=="b8-b6" for m in s.moves());a=search(s,1,BLACK,False,False);b=search(s,1,BLACK,True,True,True);assert a.move and b.move and abs(a.score-b.score)<1e-9 and b.stats.trace;print("Self-test OK")
if __name__=="__main__":
 import sys
 if "--test" in sys.argv:self_test()
 else:
  if tk is None:raise SystemExit("Tkinter не встановлено. У Linux: sudo apt install python3-tk")
  root=tk.Tk();App(root);root.mainloop()

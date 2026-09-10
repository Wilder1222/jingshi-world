"""同一坐标生成P01镜头用俯视/侧视；不是车辆制造或承载验证。"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '资产/空间校核'


def build():
    # 米仅用于虚拟资产统一比例，全部为待人物/马匹组合验证的设计提案。
    d = dict(units='m', status='blocking_proposal_not_engineering',
             cabin_x=[0.9, 3.9], cabin_width=1.8, floor_z=1.05, roof_z=2.7,
             driver_x=[0.1, 0.85], rear_rack_x=[4.0, 4.75],
             door_x=[1.5, 2.3], door_top_z=2.55, hinge='rear_vertical_jamb',
             step_x=[1.45, 2.35], step_z=0.55, step_depth=0.32,
             axles_x=[0.4, 3.35], wheel_radii=[0.55, 0.65],
             rear_bench_x=[3.25, 3.8], front_partition_x=0.9,
             moving_front_axle='visual pivot placeholder; turning sweep unverified',
             convoy={'front_left':'C16 / H01', 'front_right':'C17 / H02',
                     'rear_left':'C20 / H05', 'rear_right':'C23 / H08',
                     'driver':'C03', 'passenger':'C01', 'draft_horses':4})
    checks = {
        'step_below_floor': d['step_z'] < d['floor_z'],
        'step_clear_front_wheel_side_projection': d['step_x'][0] > d['axles_x'][0] + d['wheel_radii'][0],
        'step_clear_rear_wheel_side_projection': d['step_x'][1] < d['axles_x'][1] - d['wheel_radii'][1],
        'door_before_rear_seat': d['door_x'][1] < d['rear_bench_x'][0],
        'luggage_behind_cabin': d['rear_rack_x'][0] > d['cabin_x'][1],
        'driver_outside_front_partition': d['driver_x'][1] < d['front_partition_x'],
    }
    if not all(checks.values()):
        raise ValueError('P01空间提案基本关系冲突')
    d['checks'] = checks
    d['unverified'] = ['人物坐姿与扶行实测', '轴架与载荷', '前轮转向扫掠', '四马并列挽具', '轮旁人马动态间距', '门阶实作']
    OUT.mkdir(exist_ok=True)
    (OUT / 'P01-空间基准.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="1230" viewBox="0 0 1260 1230">',
           '<rect width="1260" height="1230" fill="#f6f3ec"/>',
           '<style>text{font-family:Microsoft YaHei,sans-serif;fill:#24333b;font-size:17px}.title{font-size:26px;font-weight:bold}.small{font-size:14px}.line{stroke:#344951;stroke-width:2;fill:none}</style>']
    def text(x,y,t,cls=''):
        svg.append(f'<text x="{x}" y="{y}" class="{cls}">{t}</text>')
    def rect(x,y,w,h,fill,stroke='#344951'):
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    def line(x,y,X,Y,color='#344951',dash=False):
        svg.append(f'<line x1="{x}" y1="{y}" x2="{X}" y2="{Y}" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')
    scale=160
    X=lambda x:310+x*scale
    text(45,45,'P01 马车空间基准｜同坐标俯视 + 右侧视','title')
    text(45,76,'暂定虚拟尺度，用于统一镜头和资产；不是实车制造、承载或驾乘验收。')
    text(45,112,'行进方向 ←　前在左 / 后在右；车辆右侧位于俯视图下方。')
    text(45,150,'01 俯视｜去顶示意，实际车厢保持不透明','title')
    y=205
    rect(X(.9),y,3*scale,1.8*scale,'#dce4e3')
    rect(X(.1),y+40,.75*scale,208,'#d6c2a5')
    rect(X(3.25),y+15,.55*scale,258,'#929dad')
    rect(X(4),y+15,.75*scale,258,'#d6c2a5')
    for x in d['axles_x']:
        line(X(x),y-18,X(x),y+306,'#6b7377',True)
        for wy in [y-27,y+296]:rect(X(x)-43,wy,86,18,'#626b70')
    line(X(-1.5),y+144,X(.1),y+144)
    text(X(-1.45),y+130,'牵引连接待核','small')
    text(X(.14),y+130,'韩青','small');text(X(.13),y+153,'前驾座','small')
    text(X(1.0),y+90,'实体前隔板','small')
    text(X(2.8),y+185,'后座 →','small')
    text(X(4.05),y+112,'P02','small');text(X(4.05),y+143,'C23包','small');text(X(4.05),y+174,'车尾行李','small')
    # Right door hinge at rear jamb, open outward; step independent of leaf.
    rect(X(1.45),y+288,.9*scale,.32*scale,'#e5c98f')
    line(X(1.5),y+288,X(2.3),y+288,'#b24639',True)
    line(X(2.3),y+288,X(2.3),y+288+.8*scale,'#b24639')
    svg.append(f'<path d="M {X(1.5)} {y+288} A 128 128 0 0 0 {X(2.3)} {y+416}" fill="none" stroke="#b24639" stroke-dasharray="6 5"/>')
    text(X(2.4),y+365,'右门后缘竖铰链；门扇向外开','small')
    text(X(1.0),y+365,'踏阶独立固定','small')
    text(45,652,'02 右侧视｜与俯视共用前后坐标','title')
    Z=lambda z:1130-z*160
    line(45,Z(0),1200,Z(0),'#adb3ad')
    rect(X(.9),Z(2.7),3*scale,(2.7-1.05)*160,'#dce4e3')
    rect(X(.1),Z(1.25),.75*scale,24,'#d6c2a5')
    rect(X(4),Z(1.05),.75*scale,12,'#d6c2a5')
    for x,r in zip(d['axles_x'],d['wheel_radii']):
        # Both views use the same uniform scale.
        svg.append(f'<ellipse cx="{X(x)}" cy="{Z(r)}" rx="{r*scale}" ry="{r*160}" fill="#bbc2c0" stroke="#344951" stroke-width="3"/>')
        line(X(x)-r*scale,Z(r),X(x)+r*scale,Z(r))
    rect(X(1.5),Z(2.55),.8*scale,(2.55-1.05)*160,'#f6f3ec')
    rect(X(1.45),Z(.55),.9*scale,8,'#e5c98f')
    for x in [1.48,2.32]:line(X(x),Z(1.05),X(x),Z(.55),'#80684b')
    text(X(1.51),Z(1.9),'右侧门','small')
    text(X(2.5),Z(1.13),'地板 1.05 m','small')
    text(X(2.45),Z(.5),'踏阶 0.55 m','small')
    text(X(4.02),Z(1.4),'后架','small')
    text(45,1175,'双视图统一 160 px/m；暂定镜头空间提案，需人物、马匹及实作复核。','small')
    svg.append('</svg>')
    (OUT/'P01-空间基准.svg').write_text('\n'.join(svg),encoding='utf-8')
    print('P01空间提案：6项静态关系通过；输出JSON及同坐标双视图，动态和制造未验证。')


if __name__ == '__main__':
    build()

# 《经世》MJ风格探索提示词

2026-09-07｜CineWeave Director 探索稿 v0.3｜43条模板｜当前范围：第一集核心资产＋两位女主参考的造型补充＋城市风格测试。提示词未执行，未生成新图片。

**审美补充 v0.3：**全库43条已接入项目共同偏好；人物强化选角美感、发式、衣装工艺与光色，场景及道具强化材质、构图与色彩，现代局部镜头承接精致摄影。四位首批人物的具体五官沿用v0.2，新风格已直接写入可复制的英文提示词。共同依据见[美术风格与造型总则](../../美术风格与造型总则.md)。

**人物修订 v0.2：**先用[首批人物重写版](首批人物提示词-v0.2.md)里的四条替换上一批人物测试。已明确中国男性主体，分别细化四人的五官、发式、体态与表情，并同步顾砚衣伤状态、柔雾对照及书房双人模板；场景和道具的形制与摆位沿用原版。新增形态细节仍是探索提案，尚未成为选定角色形象。

先看[raw参考评估](raw参考评估.md)。本轮采用用户明确的“华丽、高端、偶像古装剧集风格”：出众选角、精美服化道、柔和立体的面部光、浓郁通透的冷暖色彩和细腻材质。衣伤、身份、场景拓扑沿用现有资产卡，未知器形和具体摆位是可改的设计提案。全剧成片16:9；人物肖像3:4、道具4:3是制作参考画幅，不改变成片画幅。

## 先跑这10条

| 顺序 | 模板 | 用来决定什么 |
|---|---|---|
| 1 | EXP-C01 顾砚 | 青年主角的脸、军旅气质、棉毛行旅服是否成立 |
| 2 | EXP-C03 韩青 | 与顾砚区分，又能属于同一部剧 |
| 3 | EXP-C04 顾伯 | 老年人的骨相、细纹与温度能否和青年同框 |
| 4 | EXP-C16 杜长庚 | 成熟老卒与褐围巾，避免全队少年脸 |
| 5 | EXP-S04 书房 | 木作、灯光、门窗柜与镜子的整体质感 |
| 6 | EXP-T01 人物进书房 | 脸、衣服、空间、光线放到一起是否协调 |
| 7 | EXP-S03 顾府外院 | 旧宅的底蕴与生活痕迹，院地保持可通行 |
| 8 | EXP-S01 春泽桥 | 冷雨、暖光、湿石和可读空间是否成立 |
| 9 | EXP-P02 私人行囊 | 棉布、重量、磨损的美术尺度 |
| 10 | EXP-P16 铜片 | 金属工艺、磨损与虚构元素的分寸 |

可以先完成前6条看人物和室内，再补后4条。每条先留一轮结果；选出喜欢的方向后才扩其余人和状态。此处不预估点数或声称每条的实际成本。

如果拿不准“该多梦幻”，比较EXP-C01与EXP-C01-DIFFUSE、EXP-S04与EXP-S04-DIFFUSE。只换柔雾描述，保留其他文字、设置与参考；同一轮可使用相同实际seed辅助比较，但seed不能锁定角色身份。[MidJourney Seeds说明](https://docs.midjourney.com/hc/en-us/articles/32604356340877-Seeds)

## 提交设置与版本

你已确定**MidJourney 8.2网页端**出图、小云雀视频、剪映剪辑。下方参数按该模型与入口编写，可在网页Imagine栏使用。账号中的个人化、固定参考和其他隐藏设置仍由你在提交前检查一次；本文件不声称读取过你的账号。

2026-09-07已核查官方：[V8.2为当前默认版本](https://docs.midjourney.com/hc/en-us/articles/32199405667853-Version)。本文件不沿用旧版的角色引用语法，也没有添加未经确认的质量或高清参数。

使用时做一次设置检查即可：

1. 选择V8.2；本轮建议关闭Personalization、Moodboard以及此前固定的图片／风格参考，避免旧偏好混入。
2. 保持Raw开启、Stylize 75、Chaos 0、Weird 0。75是本项目的探索起点，不是平台推荐最优值；Raw和Stylize的作用见[Raw](https://docs.midjourney.com/hc/en-us/articles/32634113811853-Raw)与[Stylize](https://docs.midjourney.com/hc/en-us/articles/32196176868109-Stylize)。
3. 复制某一条英文代码块作为完整提示词，贴入MidJourney网页Imagine输入区。
4. 代码块默认**纯文本、不挂参考图**。两位女主图可用于你对照审美，暂不把她们的脸或浅色衣装输入其他角色的身份参考。
5. 保存原始下载图和实际提交设置。若界面自动改写参数，记录真实结果，不用本文件参数冒充实际值。

参数只放在正文末尾，写法依据[官方Parameter List](https://docs.midjourney.com/hc/en-us/articles/32859204029709-Parameter-List)。画幅参数不规定像素大小；写“8K”也不会证明图是高清。[官方Aspect Ratio说明](https://docs.midjourney.com/hc/en-us/articles/31894244298125-Aspect-Ratio)

## 怎么使用参考，以及避免风格混在一起

- 宁清晏图：可参考月白银绣、发饰层次、光线；她的脸只作为C27候选。
- 殷照夜图：可参考回眸响应与面容；衣色另探索石榴红／深紫，减少遮住眼睛的柔雾。
- 院落图：可参考木作、屋檐层次和门廊框景；顾府不继承中央水池、富丽规模和参考人物。
- 城市图：补全后的原图已查看，可借层叠楼阁、舟船水岸和大气透视；全城水网和城楼位置不自动定为正典。
- 下一轮要使用Style Reference时，先选哪张承担哪项风格；不能把Style Reference当保脸工具。官方将其定义为风格而非人物／物体复制机制。[Style Reference说明](https://docs.midjourney.com/hc/en-us/articles/32180011136653-Style-Reference)

本轮代码块不用文件路径、图片URL、`--sref`、`--oref`或账户风格代码。原创新角色不会从参考图自动继承某张脸。纯文本的新角度和衣伤图也可能换脸；选定脸后，再通过实际支持的参考／编辑方式做同一人的扩展。

## 完整提示词库

下方EXP编号仅为本次探索任务标签，不是新增角色／场景／道具编号。每条都有原资产来源与检查点；同一资产的多个EXP仍使用原C／S／P身份。

## 角色

### EXP-C01｜顾砚：原顾与今顾共用

归属：C01、C02。检查：明确中国男性；24岁长鹅蛋脸、平直浓眉、细长杏眼、浅内双、清楚唇峰；目光克制、略疲惫；原顾今顾同脸。。

```text
Waist-up casting portrait of a handsome Chinese man, 24 years old, with a lavish, high-end Chinese costume idol drama aesthetic. A long oval face with clearly defined cheekbones, a lean lower face and a softly rounded chin. Thick straight black eyebrows sit above slender almond-shaped dark-brown eyes, shallow inner eyelid folds and subtly tapered outer corners. A straight nose bridge with a moderate root, a defined cupid's bow and a slightly fuller lower lip. Warm wheat-toned skin, faint under-eye fatigue, clean-shaven face. Long straight black hair is gathered into one neat topknot secured with a small dark wooden hairpin. A tall lean athletic frame, open shoulders, level chin; his gaze holds steady and his lips rest closed, as though keeping an explanation to himself. A fitted ink-blue cross-collar travel robe with smoky-gray inner layers, dense cotton twill, fine wool, narrow sleeves and a plain belt. Eye-level camera, quiet gray plaster background, soft directional daylight, gentle warm rim light, visible skin texture and cloth weave, restrained glow on bright edges. Refined leading-man beauty, graceful long neck and an elegantly fitted collar. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C01-顾砚（原顾）](../../../资产/角色/C01-顾砚（原顾）.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C03｜韩青

归属：C03。检查：明确中国男性；25岁脸比顾砚短宽、眉眼开阔、鼻头圆实；肩臂结实、嘴角放松；灰青窄袖。。

```text
Waist-up casting portrait of a handsome Chinese man, 25 years old, a young former frontier soldier with a lavish, high-end Chinese costume idol drama aesthetic. A compact face, broad through the cheeks, with firm cheek volume and a clean square jaw tapering to a rounded chin. Straight eyebrows with slightly lifted tails frame broad almond-shaped dark-brown eyes with visible upper eyelid creases and open outer corners. A straight medium-width nose with a rounded tip, naturally full lips and relaxed mouth corners. Sun-tanned warm skin with a lighter area beneath the collar, clean-shaven face. Long black hair is pulled firmly into a compact topknot tied with a gray-blue cloth band. Strong shoulders and forearms, a natural athletic build. His torso turns slightly toward someone beside the camera; alert eyes check that person's condition, his mouth relaxed without a broad smile. A gray-blue cross-collar travel jacket with narrow sleeves, dense cotton over thin wool, neatly finished cuffs and a plain waist belt. Eye-level camera, quiet gray plaster background, soft directional daylight, gentle warm rim light, visible skin texture and cloth weave, restrained glow on bright edges. Bright, athletic leading-man appeal, meticulously arranged hair and crisp collar layering. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C03-韩青](../../../资产/角色/C03-韩青.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C04｜顾伯

归属：C04。检查：明确中国男性；64岁圆方脸、饱满面颊、稍垂眼尾、短灰白须；保留年龄纹理与挂念神情。。

```text
Waist-up casting portrait of a dignified Chinese man, 64 years old, a longtime household caregiver with a lavish, high-end Chinese costume idol drama aesthetic. A rounded square face, full forehead, softly filled cheeks and a short broad chin. Gently curved gray-black eyebrows, dark-brown eyes with slightly lowered outer corners, folded upper lids, fine crow's feet and natural under-eye bags. A softly rounded nose tip and thin relaxed lips. A neatly trimmed short gray-white moustache and beard follow the chin, leaving the cheeks visible. Warm light-medium skin with forehead lines, fine creases around the mouth and a few small age spots. Thinning salt-and-pepper hair is gathered into a modest small bun. His shoulders relax while his back remains upright; his mouth is closed, a small crease between his brows suggests concern. Both hands rest loosely together at waist level, showing tendons and age. A clean, well-kept tea-brown cotton robe, warm-gray inner collar and tiny precise repairs at the cuffs. Eye-level camera, quiet gray plaster background, soft directional daylight, gentle warm rim light, visible skin texture and cloth weave, restrained glow on bright edges. Distinguished mature elegance, neatly groomed short silver beard and softly draped, carefully finished cotton layers. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C04-顾伯](../../../资产/角色/C04-顾伯.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C16｜杜长庚

归属：C16。检查：明确中国男性；43岁方长脸、宽下颌、平阔下巴、横向窄眼、微白鬓角；褐围巾、平视站定。。

```text
Waist-up casting portrait of a handsome Chinese man, 43 years old, a former frontier squad leader with a lavish, high-end Chinese costume idol drama aesthetic. A long rectangular face, broad angular jaw and wide level chin. Dense low-set straight eyebrows above narrow horizontal almond-shaped dark-brown eyes, slightly hooded upper lids and a fine vertical crease between the brows. A straight moderately broad nose bridge, thin upper lip and a firm closed mouth line. Weathered warm medium skin, fine lines at the eye corners, clean-shaven cheeks. Long black hair is tied in a compact plain topknot, with distinct fine gray strands at both temples. A broad-shouldered sturdy build, shoulders settled, chin level and gaze resting steadily just beside the camera. A brown fine-wool scarf lies close around his neck over a dark brown-gray cross-collar travel jacket, fitted shoulders, narrow sleeves and a practical waist belt. Carefully bound seams and softened old folds remain visible. Eye-level camera, quiet gray plaster background, soft directional daylight, gentle warm rim light, visible skin texture and cloth weave, restrained glow on bright edges. Striking mature masculine elegance, meticulously arranged graying temples and rich fine-wool texture. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C16-杜长庚](../../../资产/角色/C16-杜长庚.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C17｜石照川

归属：C17。检查：宽肩方脸靛布；正常体量而非巨人。

```text
Waist-up portrait of a handsome 38-year-old veteran with a square face, a broad brow, open eyes and a strong jaw. His broad shoulders and deep chest have natural proportions. He wears an indigo dense-cotton outer jacket over dark gray wool, fitted at the waist. His expression is quiet and grounded. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C17-石照川](../../../资产/角色/C17-石照川.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C18｜孟宽

归属：C18。检查：粗眉短须赭腰带；保留生活感。

```text
Waist-up portrait of a handsome 36-year-old veteran with a broad rectangular face, coarse eyebrows, a short beard and strong arms. He wears a smoky-gray travel jacket over dark brown layers with a clearly visible russet waist sash. His mouth holds back a small smile while his eyes remain alert. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C18-孟宽](../../../资产/角色/C18-孟宽.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C19｜罗百泉

归属：C19。检查：长脸灰须，与顾伯杜长庚年龄及轮廓区分。

```text
Waist-up portrait of a handsome 45-year-old veteran with a long face, open brow, a neatly trimmed gray beard and a lean upright neck and shoulders. He wears a softly worn gray-brown travel robe with a lighter inner collar, carefully aligned seams and cotton-wool layers. His expression is patient and composed. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C19-罗百泉](../../../资产/角色/C19-罗百泉.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C20｜崔望野

归属：C20。检查：瘦长短披肩；弓包防雨布，无刺客面罩。

```text
Waist-up portrait of a handsome 34-year-old veteran with a narrow face, level cheekbones, fine firm eyebrows, long eyes and a tall lean build. His dark-gray short wool shoulder cape lies over a gray-blue narrow-sleeved jacket. A fabric-wrapped bow rests beside his shoulder. His gaze is focused, his posture unobtrusive. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C20-崔望野](../../../资产/角色/C20-崔望野.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C21｜伍成

归属：C21。检查：轻瘦但非少年；浅褐短褂。

```text
Waist-up portrait of a handsome 29-year-old veteran with a narrow diamond-shaped face, bright eyes, gently full cheeks and a light but strong build. He wears a light-brown short jacket with a warm-gray inner collar, dense cotton and thin wool. His attentive face carries an easy, brief smile. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C21-伍成](../../../资产/角色/C21-伍成.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C22｜段平生

归属：C22。检查：厚实肩背、米白领巾；仍是老卒而非另加厨子。

```text
Waist-up portrait of a handsome 40-year-old veteran with a broad rounded jaw, relaxed thick eyebrows, warm eyes and a thick-set shoulder and torso silhouette. An ivory neck scarf sits over a warm-gray travel jacket with room to move. His bearing is steady and good-humored. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C22-段平生](../../../资产/角色/C22-段平生.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C23｜许照邻

归属：C23。检查：青衣窄脸，方口包属于许，与P02区别。

```text
Waist-up portrait of a handsome 32-year-old veteran with a narrow face, clean eyebrows, concentrated eyes and an evenly proportioned strong build. He wears a blue cotton travel jacket over smoky-gray layers. A square-mouthed personal cloth travel bag rests beside him, its ties neatly arranged. His gaze is attentive and precise. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C23-许照邻](../../../资产/角色/C23-许照邻.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C06｜黄祁：先定无遮挡基础脸

归属：C06。检查：本张为辨脸定妆试验；正片另加既定雨帽面巾。

```text
Waist-up portrait of a handsome 34-year-old man with a long rectangular face, high defined cheekbones, angular brows, narrow eyes and a tall taut build. His dark hair is neatly tied up and his face is unobstructed for this costume portrait. He wears a matte black narrow-sleeved travel jacket over charcoal layers. His gaze is controlled and intent. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C06-黄祁](../../../资产/角色/C06-黄祁.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C07｜罗顺：先定无遮挡基础脸

归属：C07。检查：与黄祁不同脸形；正片雨帽另做状态。

```text
Waist-up portrait of a handsome 26-year-old man with a short square-rounded face, thick straight eyebrows, open eyes, a firm jaw and strong neck and shoulders. His face is unobstructed for this costume portrait. He wears a gray-brown short travel jacket with a muted blue inner collar, practical tied hair and gathered sleeves. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C07-罗顺](../../../资产/角色/C07-罗顺.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C08｜孙福生

归属：C08。检查：有体面的摊主；不靠油污或过度衰老制造身份。

```text
Waist-up portrait of a dignified 49-year-old soup vendor with a broad balanced face, relaxed eyes, smile lines and a trimmed short beard. He has strong forearms and work-worn hands. A warm chestnut short jacket and a light-gray cloth apron fit neatly. He holds a plain wooden-handled ladle at waist level. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C08-孙福生](../../../资产/角色/C08-孙福生.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C09｜周成

归属：C09。检查：圆阔脸赭褐衣，普通热心街坊。

```text
Waist-up portrait of a handsome 36-year-old man with a broad forehead, thick eyebrows, a rounded jaw, bright eyes and sun-warmed skin. His shoulders are strong from ordinary work. He wears a faded russet cotton short robe with a light-brown inner collar and neat repairs at the elbows, holding a plain ceramic soup bowl. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C09-周成](../../../资产/角色/C09-周成.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-C10｜丁茂

归属：C10。检查：长脸灰绿衣，与周成有区别，无监视者造型。

```text
Waist-up portrait of a handsome 39-year-old man with a narrow rectangular face, gently straight eyebrows, softly set eyes and a slim tall build. He wears a gray-green cotton short robe with a smoky-brown inner collar and a neatly closed front. His expression is calm and considerate. Centered at eye level, quiet gray plaster background, soft directional daylight and a gentle warm rim, clear eyes and skin texture, visible cloth weave, restrained glow on bright edges. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C10-丁茂](../../../资产/角色/C10-丁茂.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

## 场景

### EXP-S01｜春泽桥：雨夜空间

归属：S01。检查：桥面完整、泥道可通；弃车与通行关系成立。

```text
An intact old stone bridge at the edge of a fictional Chinese imperial capital on a cold rainy night. A continuous muddy footpath runs beside the cart road and joins the near bridgehead. One small open-canopy wooden cart stands at the bridgehead, its front wheel caught against a broken wooden shaft; the adjacent footpath remains open. Deep blue-gray rain and warm distant eave lamps reveal wet stone and readable ground planes. Eye-level wide establishing view, layered depth, clear material detail, photographic period-drama set. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S01-春泽桥与入城接道](../../../资产/场景/S01-春泽桥与入城接道.md)。

### EXP-S02｜南街汤摊：生活尺度

归属：S02。检查：人间烟火；不用宫殿广场替代狭街，无节庆灯海。

```text
A lived-in street in a fictional Chinese imperial capital after light night rain, timber shopfronts and layered eaves receding along a walkable lane. A modest soup stall sits beneath warm lantern light, steam rising from its pot, plain bowls and a ladle on a worn wooden counter, stacked baskets beside a closing shop. Wet paving reflects small pools of amber light. Eye-level wide view, human-scale street, readable wood joinery and cloth awnings, photographic period-drama set. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S02-南街汤摊与顾府外街口](../../../资产/场景/S02-南街汤摊与顾府外街口.md)。

### EXP-S03｜顾府外院：有底蕴的旧宅

归属：S03。检查：取院落参考木作层次；保持铺石通路、西厢；不搬中央水池。

```text
The outer courtyard of a once prosperous Chinese family residence, viewed northward from its street gate. A modest front hall stands across a continuous gray-stone paved forecourt, a single-storey west side lodging wing opens onto the courtyard, covered corridors connect the buildings. Faded deep-red door paint, finely joined dark timber repaired in places, worn stone and an old basin catching a roof drip. A rainy night with warm practical lanterns and cool ambient light, human-scale architecture, photographic period-drama set, crisp wood detail and gentle highlight rolloff. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S03-顾府门院前厅与西厢](../../../资产/场景/S03-顾府门院前厅与西厢.md)。

### EXP-S04｜书房：初醒的空间

归属：S04。检查：门—案镜—窗柜接触关系可读，光源一致，无卧床祭坛。

```text
A small old Chinese study at night, viewed from its doorway. A finely made worn wooden desk stands beside a bronze mirror and a warm oil lamp. A shuttered window faces the inner courtyard, with a low wooden cabinet beneath it; the door has a visible interior wooden sliding bolt. Deep warm timber, softly cool light through paper lattice panels and a local amber pool around the lamp. Walkable floor space connects the door, desk and window. Eye-level wide view, clear foreground and middle-ground furniture, photographic period-drama set. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S04-书房](../../../资产/场景/S04-书房.md)。

### EXP-S06｜外库门口：首夜

归属：S06。检查：只做S06-K门外夜景，无封条、不展示库内或隐室。

```text
The closed ordinary wooden door of a storage room on the east side of the rear yard of an old Chinese family residence, reached by a short covered passage. A rain-darkened stone threshold, repaired door panels and finely aged timber match the adjoining modest house. Warm lantern light reaches the doorway from the passage, cool rainy night beyond the eaves. Oblique eye-level exterior view, only the threshold and outer door are visible, photographic period-drama set. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S06-后院与外库门口](../../../资产/场景/S06-后院与外库门口.md)。

### EXP-S07｜现代岩壁：已安全落地的记忆

归属：S07。检查：只拍手袖绳岩与落地关系，无脸无坠落。

```text
A close outdoor view at the foot of a natural climbing rock face in daylight. A chalk-dusted adult man's hand has just left the rock, a modern outdoor sleeve visible at the wrist; a loose climbing rope hangs on the right. At the bottom of the composition his shoes rest firmly on level ground. Real rock grain, chalk traces and rope fibres, clear natural daylight, cinematic photographic detail. Polished live-action cinematography for the modern insert of the series: luminous natural color, delicate highlight rolloff and tactile material detail. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S07-现代岩壁局部](../../../资产/场景/S07-现代岩壁局部.md)。

## 编号道具

### EXP-P01｜敞棚小车：形制

归属：P01。检查：车形探索；牵引动物种类和数量仍未定，此图不宣称完整行进装配。

```text
A small open-canopy wooden passenger cart for an injured traveller, a simple timber frame, woven cloth canopy, practical wooden wheels and visible reins. Three-quarter side view on level gray ground, plain uncluttered background, believable human scale, restrained metal fittings, worn joinery, softly lit cotton canopy folds. Photographic historical prop study. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P01-敞棚小车](../../../资产/道具/P01-敞棚小车.md)。

### EXP-P02｜顾砚私人行囊

归属：P02。检查：圆软轮廓为本轮区分提案；与许的方口包不同，闭合不露旧票。

```text
One small personal travel bundle made of smoky-brown dense cloth, a softly rounded closed body, a narrow practical carrying strap and neat cord ties. Damp creases along the lower edge, restrained wear at the seams, placed alone on a plain aged wooden table. Three-quarter close view, soft side daylight, clearly visible fabric weave and natural weight. Photographic historical prop study. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P02-顾砚私人小行囊](../../../资产/道具/P02-顾砚私人小行囊.md)。

### EXP-P09｜碎杯与瓷片：初醒地面

归属：P09。检查：普通碎杯和清水；不新增毒药、符号或血池。

```text
Fragments of a plain pale ceramic cup on the worn wooden floor beside a Chinese study desk, a small puddle of clear water between several larger curved shards. Warm lamplight reflects along the wet edges, soft cool ambient light fills the shadows. Low oblique close view, sharp ceramic thickness and natural contact shadows, photographic prop detail. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P09-碎杯与瓷片](../../../资产/道具/P09-碎杯与瓷片.md)。

### EXP-P10｜顾伯照料物：前厅

归属：P10。检查：普通照料，非仪式；物件组合用于风格比较不当镜头位置定版。

```text
A folded clean cotton cloth beside a small well-used wooden medicine box and a plain ceramic bowl of warm rice porridge on an old Chinese household table. A simple spoon rests beside the bowl. Fine repairs in the cloth, warm wood grain and gentle steam are visible under soft oil-lamp light. Quiet three-quarter close view, photographic period-drama prop arrangement. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P10-顾伯布药箱粥与温水](../../../资产/道具/P10-顾伯布药箱粥与温水.md)。

### EXP-P12｜现代衣袖与绳具

归属：P12。检查：现代局部、不带入古代；具体绳结不作为操作教学。

```text
Close detail of an adult climber's chalk-dusted hand and modern outdoor sleeve beside a slack woven climbing rope on natural rock at ground level. The hand is relaxed, the rope lies without tension. Daylight reveals individual rope fibres, chalk on the fingers and matte sleeve fabric. Photographic outdoor equipment detail. Polished live-action cinematography for the modern insert of the series: luminous natural color, delicate highlight rolloff and tactile material detail. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P12-现代局部衣袖与绳具](../../../资产/道具/P12-现代局部衣袖与绳具.md)。

### EXP-P14｜顾伯备下的干衣

归属：P14。检查：浅灰干衣；不设计成新礼服、不当作湿血旅衣。

```text
A neatly folded light-gray cotton inner robe with an overlapping collar, fine straight stitching and softly weighted fabric, placed alone on an old wooden bench. The sleeve edge and collar construction are clearly visible. Soft warm side light, restrained sheen, a slightly darker gray lining. Photographic Chinese period-drama costume detail. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P14-顾伯所备干衣](../../../资产/道具/P14-顾伯所备干衣.md)。

### EXP-P16｜退制阵甲铜片：材质

归属：P16。检查：尺寸和纹样是原创探索提案；先看未发光材质，九人份不做九片悬浮阵盘。

```text
One palm-sized worn copper plate with restrained shallow geometric grooves, rounded edges, oxidized recesses and rubbed warm-metal high points. A simple dark cloth fastening lies beside it on a neutral gray surface. Three-quarter macro view, directional soft light reveals shallow engraving and years of wear. Unlit metal, photographic historical fantasy prop study. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P16-九片退制阵甲铜片](../../../资产/道具/P16-九片退制阵甲铜片.md)。

## 补充状态与器物

### EXP-S03-W｜西厢：九卒临时住处

归属：S03。检查：西厢属于S03；是临时住处，不是外库或已定每人铺位。

```text
Inside the west lodging wing of an old Chinese family courtyard at night, rolled bedding and separate personal cloth bags arranged along a wall, a worn cooking pot and a tied sack of rice beside a low bench. The room opens directly toward the outer courtyard through a practical timber doorway. Clean but temporary living arrangements, aged wood and cotton weave, warm lantern light, clear walkable middle floor. Photographic period-drama set. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S03-顾府门院前厅与西厢](../../../资产/场景/S03-顾府门院前厅与西厢.md)。

### EXP-S04-MIRROR｜铜镜：形制与可读反射

归属：S04。检查：椭圆形为探索提案；本图测试材质不验证人物镜像。

```text
A standing bronze mirror with a simple oval reflective face and a worn dark wooden support on an old Chinese study desk. The polished central area clearly reflects a plain section of the opposite timber wall; darker bronze remains at the rim. Warm oil-lamp light grazes the metal edge, cool ambient light preserves its surface. Oblique close view, photographic period prop detail. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[S04-书房](../../../资产/场景/S04-书房.md)。

### EXP-S04-WINDOW｜书房窗柜与窗闩

归属：S04。检查：比例草图用于验证试窗，不新增高坠或地下出口。

```text
An old inward-facing Chinese courtyard window above a low wooden cabinet in a study. The window is slightly open, a plain wooden latch rests in its fitting, the cabinet top and the courtyard ground beyond are visible in one oblique eye-level view. Fine worn joinery, softly cool night light outside and warm lamplight inside, clear believable furniture proportions. Photographic period-drama set detail. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S04-书房](../../../资产/场景/S04-书房.md)。

### EXP-C23-BAG｜许照邻方口行囊

归属：C23。检查：许的包与P02轮廓及色调可区分。

```text
One square-mouthed personal travel bag in dense muted-blue cotton, reinforced straight top edges, a flat folded cover and tidy dark cord ties, resting upright beside a wooden bench. Three-quarter close view, softly worn fabric corners, visible stitching and natural contact shadows under soft side daylight. Photographic historical prop study. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[C23-许照邻](../../../资产/角色/C23-许照邻.md)。

### EXP-C01-WET｜顾砚：雨湿肩伤状态

归属：C01、C02。检查：此纯文本候选不保证与EXP-C01同脸；定脸后依据母图再做状态。

```text
Waist-up casting portrait of a handsome Chinese man, 24 years old, with a lavish, high-end Chinese costume idol drama aesthetic. A long oval face with clearly defined cheekbones, a lean lower face and a softly rounded chin. Thick straight black eyebrows sit above slender almond-shaped dark-brown eyes, shallow inner eyelid folds and subtly tapered outer corners. A straight nose bridge with a moderate root, a defined cupid's bow and a slightly fuller lower lip. Warm wheat-toned skin, faint under-eye fatigue, clean-shaven face. Long straight black hair is gathered into one neat topknot secured with a small dark wooden hairpin. A tall lean athletic frame. An ink-blue cross-collar travel robe clings damply over smoky-gray layers; the fabric at his own left shoulder has a modest fresh tear and localized blood staining over an older injury. His right hand steadies the left arm, his lips stay closed and his gaze remains focused despite fatigue. Cool rainy night and warm light from one side, readable eyes, natural skin texture and visible cloth weave. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C01-顾砚（原顾）](../../../资产/角色/C01-顾砚（原顾）.md)。

### EXP-C01-DRY｜顾砚：干衣初包扎状态

归属：C01、C02、P14。检查：先看衣伤方案；原顾今顾使用同一个选定母版后再批量。

```text
Waist-up casting portrait of a handsome Chinese man, 24 years old, with a lavish, high-end Chinese costume idol drama aesthetic. A long oval face with clearly defined cheekbones, a lean lower face and a softly rounded chin. Thick straight black eyebrows sit above slender almond-shaped dark-brown eyes, shallow inner eyelid folds and subtly tapered outer corners. A straight nose bridge with a moderate root, a defined cupid's bow and a slightly fuller lower lip. Warm wheat-toned skin, faint under-eye fatigue, clean-shaven face. Long straight black hair is gathered into one neat topknot secured with a small dark wooden hairpin. A tall lean athletic frame. He wears a light-gray cotton inner robe, the collar arranged around a modest clean bandage at his own left shoulder, the left arm resting without effort. His eyes pause on the room with wary attention; warm lamplight with gentle cool fill reveals natural skin texture and fine collar stitches. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C02-陈渡（今顾）](../../../资产/角色/C02-陈渡（今顾）.md)。

### EXP-C01-BLOODROBE｜换下旅衣：悬挂状态

归属：C01、S03。检查：复用主角雨衣设计；不把P14干衣挂成血衣。

```text
An empty ink-blue travel robe hanging from a simple wooden corridor rack in an old Chinese residence at night. Damp fabric falls with real weight; a small tear and localized dried blood mark the garment's wearer-left shoulder. Warm light from a nearby room catches the weave, cool rain light reaches the outer hem. Clear three-quarter prop view, photographic period-drama costume detail. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[P14-顾伯所备干衣](../../../资产/道具/P14-顾伯所备干衣.md)。

### EXP-C01-SCABBARD｜顾砚刀鞘与随身刀：工艺方向

归属：C01。检查：单刃刀形属于本轮器形提案，不写回既定设定；不安排实战操作或新增铭文。

```text
A practical single-edged travel saber resting beside its plain dark wooden scabbard on neutral gray cloth. A restrained iron guard, a tightly wrapped dark grip and worn scabbard fittings, balanced human-scale proportions and believable aged craftsmanship. Soft directional daylight reveals metal edges, cord fibres and rubbed wood. Photographic Chinese period-drama prop study. Art-department prop photography with a lavish, high-end Chinese costume idol drama aesthetic: exquisite rendering of the specified materials, finely resolved craftsmanship, luminous color and softly graduated highlights, preserving the described construction and wear. --ar 4:3 --v 8.2 --raw --s 75 --c 0
```

依据：[C01-顾砚（原顾）](../../../资产/角色/C01-顾砚（原顾）.md)、[GJ-EP01-归京](../../../剧集/01-归京/GJ-EP01-归京.md)。

## 同场验证

### EXP-T01｜人物进入书房：全剧质感检验

归属：C01、C02、C04、S04、P14。检查：中国男性双人同场；顾砚长鹅蛋脸与顾伯圆方脸、短灰须区分；仅质感试验，同脸仍需已选母图。。

```text
Inside a modest old Chinese study at night, two Chinese men beside a worn wooden desk. Seated on the left, a handsome 24-year-old man has a long oval face, defined cheekbones, thick straight eyebrows, slender dark-brown almond eyes, a straight nose and a defined cupid's bow. Warm wheat-toned skin, faint under-eye fatigue, clean-shaven; long black hair in a neat topknot with a dark wooden hairpin. He wears a light-gray inner robe, his own left shoulder simply bandaged, his gaze fixed on the room. Standing on the right, a dignified 64-year-old caregiver has a rounded square face, full cheeks, slightly lowered outer eye corners and a neatly trimmed short gray-white beard. Salt-and-pepper hair in a modest bun, tea-brown robe and warm-gray collar. He holds a small lamp, mouth closed, brow faintly furrowed with concern. A bronze mirror and low window cabinet remain visible. Medium two-person composition, warm practical lamplight and cool paper-window fill, clear faces, aged timber and cloth weave, delicate glow limited to the lamp. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[GJ-EP01-归京](../../../剧集/01-归京/GJ-EP01-归京.md)、[S04-书房](../../../资产/场景/S04-书房.md)。

## 女主补充探索

### EXP-C27-LOOK｜宁清晏：降低柔雾后的造型方向

归属：C27。检查：原创文字方向；保留参考图的月白银绣气质，不宣称纯文本锁住参考脸。

```text
Waist-up portrait of a 22-year-old woman with a long oval face, gently extended eyebrows, clear eyes with level outer corners and a composed upright bearing. Her black hair is arranged in an elegant high style with restrained silver and white floral ornaments. Moon-white and icy-blue layered silk, fine tonal embroidery and a modest silver sheen. Soft directional daylight, gentle warm edge light, clear eyes, individual hair strands and visible silk weave, background highlights softly glowing. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C27-宁清晏](../../../资产/角色/C27-宁清晏.md)。

### EXP-C28-LOOK｜殷照夜：恢复红紫主色与鲜活气质

归属：C28。检查：原创造型方向；不改变用户参考脸为新定版，后续换装保脸需基于参考工具验证。

```text
Waist-up portrait of a 19-year-old woman with a slightly heart-shaped face, relaxed eyebrows, subtly lifted outer eye corners and a lively direct gaze. She turns her shoulders lightly and holds a small spontaneous smile. Her dark hair is arranged with a few fine gold ornaments. A pomegranate-red silk outer robe over deep-plum layers, a crisp fitted waist and finely embroidered edges, rich fabric colour and restrained gold highlights. Soft directional daylight, clear facial texture and eye detail, gentle glow only in the background. Live-action photography with a lavish, high-end Chinese costume idol drama aesthetic. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C28-殷照夜](../../../资产/角色/C28-殷照夜.md)。

## 单变量对照

### EXP-C01-DIFFUSE｜顾砚B：只提高柔雾扩散

归属：C01、C02。检查：比较脸部清楚程度和写真柔雾偏好；不是换一套审美或保证固定身份。

对照：EXP-C01；仅改变高光扩散／柔雾范围。保持：人物文字、衣装、机位、背景、光源、模型及参数不变；同一轮可固定相同seed，输出身份仍需比对。

```text
Waist-up casting portrait of a handsome Chinese man, 24 years old, with a lavish, high-end Chinese costume idol drama aesthetic. A long oval face with clearly defined cheekbones, a lean lower face and a softly rounded chin. Thick straight black eyebrows sit above slender almond-shaped dark-brown eyes, shallow inner eyelid folds and subtly tapered outer corners. A straight nose bridge with a moderate root, a defined cupid's bow and a slightly fuller lower lip. Warm wheat-toned skin, faint under-eye fatigue, clean-shaven face. Long straight black hair is gathered into one neat topknot secured with a small dark wooden hairpin. A tall lean athletic frame, open shoulders, level chin; his gaze holds steady and his lips rest closed, as though keeping an explanation to himself. A fitted ink-blue cross-collar travel robe with smoky-gray inner layers, dense cotton twill, fine wool, narrow sleeves and a plain belt. Eye-level camera, quiet gray plaster background, soft directional daylight, gentle warm rim light, visible skin texture and cloth weave, a stronger diffusion veil extending across both face and background. Refined leading-man beauty, graceful long neck and an elegantly fitted collar. Elegant layered costume silhouettes, finely finished collar edges, carefully groomed hair, luminous sculpting light and bright eye catchlights. Rich translucent color, warm skin against cool surroundings, delicate highlights and dimensional dark fabrics. --ar 3:4 --v 8.2 --raw --s 75 --c 0
```

依据：[C01-顾砚（原顾）](../../../资产/角色/C01-顾砚（原顾）.md)、[美术风格与造型总则](../../../资产/美术风格与造型总则.md)。

### EXP-S04-DIFFUSE｜书房B：只提高柔雾扩散

归属：S04。检查：比较木作、门闩和镜面是否仍可读；梦幻感不能遮掉叙事物件。

对照：EXP-S04；仅改变高光扩散／柔雾范围。保持：房间、陈设、机位、光源位置、模型及参数不变。

```text
A small old Chinese study at night, viewed from its doorway. A finely made worn wooden desk stands beside a bronze mirror and a warm oil lamp. A shuttered window faces the inner courtyard, with a low wooden cabinet beneath it; the door has a visible interior wooden sliding bolt. Deep warm timber, softly cool light through paper lattice panels and a local amber pool around the lamp. Walkable floor space connects the door, desk and window. Eye-level wide view, diffusion softly veiling foreground and middle-ground furniture edges, photographic period-drama set. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[S04-书房](../../../资产/场景/S04-书房.md)。

## 世界风格补充

### EXP-CITY01｜长京城市：宏观风格补充

归属：全局美术探索，非第一集新增场次。检查：借城市参考的繁盛、材质与纵深；水网、山势和具体城楼尚未定地理，不增加第一集航拍镜头。

```text
An expansive fictional Chinese imperial capital seen from a high terrace in slanting warm daylight. Dense layers of dark timber houses, gray tiled roofs and occasional taller gate towers extend into a softly hazy distance. A working waterway carries small wooden boats between lively quays and connected pedestrian bridges, red cloth banners punctuate the streets. Fine roof carpentry and near-ground human activity remain legible, warm highlights against blue-gray distance, photographic period-drama cityscape. A lavish, high-end Chinese costume idol drama aesthetic, elegantly layered composition, lustrous timber highlights, rich translucent color and finely separated warm and cool tones, preserving the described architecture and scale. --ar 16:9 --v 8.2 --raw --s 75 --c 0
```

依据：[美术总则](../../美术风格与造型总则.md)与[城市参考评估](raw参考评估.md)。

## 你回传什么，我如何接着做高清批次

优先将选中的**单张原图**放回项目，按“EXP编号＋候选序号”命名，例如 `raw/mj-explore/EXP-C01-A01.png`。这只是建议路径，尚未创建媒体。保留原文件，不只发四宫格截屏。

每个选中方案附上这些信息即可：

| 信息 | 示例／处理 |
|---|---|
| 选图及用途 | “EXP-C01-A01选脸，衣服想再素一点”；“EXP-S04-A02选光线，门位要改” |
| 原始提示词和实际模型 | 复制MidJourney显示的真实文字与版本；有风格引用或个人化时一起保留 |
| 原文件 | 原始下载图；我读取实际尺寸，判断是否清楚和可作为母版 |
| 其他任务信息 | job ID、seed、设置和参考来源能拿到就保留；拿不到标未知，无须补造 |
| 首轮投入 | 进入批量生成前再给点数或金额上限；目前只是手动探索，不执行付费批次 |

回传后的工作按实际选图推进：

1. 逐张评估，分别记下选中的脸、衣装、空间、材质和光线，避免一张好看的图把所有维度一起锁死。
2. 先扩顾砚、韩青、顾伯、杜的正侧面和所需衣伤，再做九卒其余人；C01与C02持续共用同一身体。
3. 将通过的场景视角与道具做成可复用母版，实际检查人物比例、门窗关系与受光。
4. 确认可调用的图像生成／编辑端与每批额度，先验证小批次，再扩大数量；本文件没有宣称存在可直接批量操控MidJourney的接口。
5. 高清交付以真实像素尺寸与局部细节检查为准，原生生成和后续放大分开记录。最终镜头图按16:9处理，输出规格在生成端确定后写清；提示词不能保证4K、固定脸或视频连续性。

CineWeave Director在这里负责设计、提示词、复核与批次规划；实际生成由届时可用的图像工具执行。当前43条都是待探索模板，没有新图片、运行回执或选用文件。

结构化正文与参数、原始参考SHA-256和待定状态另存[MJ提示词库.json](MJ提示词库.json)，供后续选图与批量准备读取；它是工作稿，不是可直接提交的生成任务配置。

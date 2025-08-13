# FantasySgpSystem

Latest Version: https://sgp-viewer-110810475909.us-central1.run.app/
### Up-To-Date SGP Leaderboard Preview
<img width="911" height="615" alt="image" src="https://github.com/user-attachments/assets/79d2c429-5357-4e67-a8c3-cc6b2b10c05a" />

### Rest of Season SGP Projections Preview
<img width="852" height="609" alt="image" src="https://github.com/user-attachments/assets/3889234f-53a5-4163-a176-c5be25ac6133" />

### Class and Package Diagrams 
<img width="1089" height="784" alt="classes_FantasySgpSystem" src="https://github.com/user-attachments/assets/4cf69fd4-be0c-45dc-afc7-f4753203ed5d" />

<img width="699" height="443" alt="packages_FantasySgpSystem" src="https://github.com/user-attachments/assets/d9379ee3-16a0-4ab6-9624-1e398f6b31f3" />


## SGP-based Value Above Average Last Place Player    
   
### SGP Calculations

#### Week factor
Let $w$ be weeks completed (out of a 26-week season). Use a mode-specific factor:
- Season-to-date (up-to-date): $f_{\text{s2d}}=\dfrac{w}{26}$
- Rest-of-season: $f_{\text{ros}}=\dfrac{26-w}{26}$
- Pre-season: $f_{\text{pre}}=1$


#### Notation

| Symbol | Meaning |
|---|---|
| $x_c^{(p)}$ | Player’s **counting** stat in category $c$ (e.g., HR, R, RBI, SB, W, SV, K). |
| $r_c^{(p)}$ | Player’s **rate** in category $c$ (e.g., AVG, OBP, SLG, ERA, WHIP). |
| $o_c^{(p)}$ | Player’s **opportunities** for rate $c$ (e.g., AB or PA for hitting; IP for pitching). |
| $L_c^{\text{team}}$ | Season Long **last-place team** value for category $c$, calculated from a recency-weighted historical standings best-fit line. |
| $R_c^{\text{team}}$ | Season Long **last-place team rate** for category $c$, calculated from the historical standings best-fit line. |
| $O_c^{\text{team}}$ | Season Long **average team opportunities** (e.g., AB/PA/IP) for category $c$. |
| $D_c$ | SGP denominator for $c$: average difference between adjacent teams in the standings (slope of the historical standings best fit line). |
| $N^{\text{players}}$ | Per-player scaling factor (equal to $13$ for hitter countings and $9$ for pitcher stats due to SGPs being calculated per player and $1$ for rate stats). |


### Counting categories (HR, R, RBI, SB, QS, SV+H, K, etc.)
Per-player scaling by roster size $N_{\text{players}}$ (e.g., $13$ for hitters, $9$ for pitchers). For rate stats, we set $N_{\text{players}}=1$.

---

$$
\mathrm{SGP}_{c}
= \frac{x_c^{(p)} - f \cdot \frac{L_c^{\mathrm{team}}}{N^{\mathrm{players}}}}{f \cdot D_c}
$$

---

### Rate categories (AVG, OBP, SLG, ERA, WHIP, etc.)
The methodology here involves removing the average last-place team's player stats and substituting the player in questions stats taking into account how many opportunities 
the average player gets in a year scaled down by the week factor.  This new calculated team rate is then subtracted by the wort place rate and divided by the average difference in standings, without scaling these down by the weeks completed factor or dividing the last place value by number of players on the roster as shown in the counting stats calculation:

---

$$
\mathrm{SGP}_c
= \frac{\dfrac{f R_c^{\mathrm{team}} \dfrac{N^{\mathrm{players}}-1}{N^{\mathrm{players}}} O_c^{\mathrm{team}} + r_c^{(p)} o_c^{(p)}}{f \dfrac{N^{\mathrm{players}}-1}{N^{\mathrm{players}}} O_c^{\mathrm{team}} + o_c^{(p)}} \-\ R_c^{\mathrm{team}}}{D_c}
$$

---

- Therefore, the entire expression $\frac{f R_c^{\text{team}} \dfrac{N^{\text{players}}-1}{N^{\text{players}}} O_c^{\text{team}} + r_c^{(p)} o_c^{(p)}}{f \dfrac{N^{\text{players}}-1}{N^{\text{players}}} O_c^{\text{team}} + o_c^{(p)}}$ is analogous to the $r_c^{(p)}$ in counting stats, and can be described as how much the player affects the overall team rate when substituted in for the average last place team player, assuming this average player gets league average opportunities scaled by weeks appropriately.   

---

- $r_c^{(p)}$: player’s rate in $c$
- $o_c^{(p)}$: player’s opportunities (AB/PA for OBP/SLG; IP/IP/BB for ERA/WHIP/(K/BB))
- $R_c^{\text{team}}$: average last-place team rate for $c$
- $O_c^{\text{team}}$: season long average team opportunities for $c$
- $D_c$: average difference between adjacent teams in standings for $c$

**OBP**
- $r_{\text{OBP}}^{(p)} = H + BB + HBP,\qquad o_{\text{OBP}}^{(p)} = PA - SH$ (OBP Calculation is $\frac{H + BB + HBP}{AB + BB + HBP + SF}$)

**SLG**
- $r_{\text{SLG}}^{(p)} = TB,\qquad o_{\text{SLG}}^{(p)} = AB$

**ERA**
- $r_{\text{ERA}}^{(p)} = ER \cdot 9,\qquad o_{\text{ERA}}^{(p)} = IP$ (ERA Calculation is $\frac{ER\,9}{IP}$)

**WHIP**
- $r_{\text{WHIP}}^{(p)} = H + BB,\qquad o_{\text{WHIP}}^{(p)} = IP$

**K/BB**
- $r_{\text{KBB}}^{(p)} = K, \qquad o_{\text{KBB}}^{(p)} = BB$ 


### OLD SGP Calculation Overview / Calculation Examples
This directory contains the fantasy SGP valuation system I created and use directly in my pre-season draft values, and also in-season to inform transactions.   

The crux of this valuation system is that it's based off a popular valuation system called Standing Gain Points, but with a twist: I decided to remove the barrier level stats (the stat level required to actually start gaining SGPs i.e. the average player on the last place team). This is in attempt to get a more accurate representation of how many standing points players are actually contributing above the last place team rather than just the raw SGPs used traditionally by SGP practicioners.  For example, let's say Player X will hit 30 home runs and steal 5 bases, while Player Y is projected for 20 home runs and 15 stolen bases.  The natural question is when deciding on player value is which of these players is more valuable?  Well, if the projection systems are to be trusted we need a way of valuing the weights of different categories. The famous Z-Score calculations will take the mean and standard deviation of each category and apply them to the players projections in order to get a sum of Z-scores for each player across the categories.  This form of normalization and sums are however, only valid for normally distributed statistics.  It has been shown (probably should include that in a notebook for validity) that these categories for the most part do not follow such a distribution, and therefore, the weights applied by the z-score method are not valid.  This brings us to the SGP method, which is already a heavily-utilized method by many fantasy baseball practicioners.  In this system, lets say the user is in a league where each person in the standings on average is separated by 10 home runs, and is seperated on average by 5 stolen bases.  The classical SGP method would calculate this as Player X: 30 hrs / 10 + 5 sbs / 5 = 4 and Player Y: 20 hrs / 10 + 15 sbs / 5 = 5, and therefore, Player Y is more valuable.  What this method forgets to capture is what is the minimum threshold of contributions in each category for a player to start providing SGPs above what is on the wire or even at the bottom of the rostered universe.  That drives the motivation for my system, which assumes a reasonably optimized rostered subset of players (the managers in the league are active enough to roster the best available players), and calculates the thresholds for minimum sufficient contributions as the average player on the 12th place team over the last 4 years (all of the standings for each category have been weighted by recency and averaged in order to calculate league tendencies and to account for differences in run enviornment).  

To further illustrate how this is done, off hand I have calculated that the 12th place team in home runs and stolen bases average a total of 241.3 home runs and 97 stolen bases.  That means, in a league where 13 hitters are rostered, this equates to 18.56 home runs and 7.5 stolen bases per year by the average player on the basement dweller team.  Thus, if a hitter is only contributing 5 stolen bases but hitting 30 home runs, he is positively contributing to your home runs above the last place threshold, but is actually providing negative value and not increasing your sb total above what the last place team is doing a per player rate.  Simply put, this ultimately results in my SGP equation of: ((player_stat__cat_i) - (last_place_team_avg_stat_cat_i/13)) / average_diff_in_standings_cat_i.  For the case mentioned above this means Player X would have a SGP of (30-18.56)/10 + (5-7.5)/5= 1.1433-0.5=.64 and Player Y's result would be (20-18.56)/10 + (15-7.5)/5 = 1.64.  Here, Player Y still wins, but I arbitrarily picked the average standing difference of 10 home runs and 5 stolen bases when in reality the values for my personal league are 7.3 home runs and 12.55 stolen bases which means that hoe runs are almost 2x as valuable as stolen bases past the respective thresholds.  

In fact, for just these two categories for these two specific hypothetical cases using the actual average standing differences and the 12th place team's average player values of 18.56 and 7.5, Player X would have a SGP of 1.369 and for Y it would be .7933, emphasizing the importance of home runs in my league over the years.  Of course, my league isn't just these two categories as we also use R, RBI, OBP, and SLUG, which makes it even more intuitive that these settings would cause home runs to be more valuable than stolen bases.  The sum of all these categories SGPs for each player utilizing various projection systems is the exact ordering I use in my pre-season draft rankings.  As you might suspect, the rate stats (OBP and SLUG) are a little more complex, and require the use of the average player's and team's opportunities across the year in regards to PAs and ABs.  A more in depth look at the calculations can be found in the code.

A fair quesiton at this point is how much added value does this bring over the standard SGP calculations, and the answer is at this point I have not looked into that, and I'm honestly willing to bet it isn't as big of a difference as I'd hope it would be.  However, in theory this is more mathematically sound, even despite some major assumptions and faith in an accurate projection system and consistency in the league's tendencies/run environment which also hold true with the original SGP system itself.

### Original Workbook 
The original (not up to date) valution system workbook itself can be found in the excel macro-enabled workbook titled LeagueStatsSGPInvest.xlsm. Included in this workbook is all of the pre-season and weekly rest of the season updated player valuations along with my league's historical data, and this workbook will continued to be improved upon and soon will become outputs from a python script that will ensure that this is periodically updated and so that the computations can be abstracted out and sped up.  It was created in the off-season prior to the 2024 MLB season and contains multiple in-season updates in order to continously drive actionable decisions for my team. 

### PS
If you're in my league, congratulations you have found what I have been ranting on about for months.  

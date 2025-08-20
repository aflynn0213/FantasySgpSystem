# FantasySgpSystem

## Introduction
The Fantasy SGP System is a comprehensive project that was born as an excel workbook with an absurd amount of sheets used to inform my Fantasy Baseball drafting strategy, and has evolved into the Full-Stack application presented here.  It involves a web-scraping and data processing python backend, Docker containers deployed using GCP, and finally, the streamlit web application to display all the necessary information for informing decisions such as pre-season draft rankings, in-season player rankings, and rest of season valuations.  The motivation for this was born out of the original [Standings Gain Points](https://www.smartfantasybaseball.com/2013/03/create-your-own-fantasy-baseball-rankings-part-5-understanding-standings-gain-points/) system, which is used commonly by fantasy baseball practicioners playing in a [ROTO](https://www.rotoballer.com/how-to-play-fantasy-baseball-roto-rotisserie-leagues-overview/1137359) format.  The premise behind ROTO is teams are awarded points based off where they place in the standings in each category independently, where points for a specified category are awarded on a scale of $\text{ROTO}_c \in [1,\text{number of teams}]$ in reverse order of standings, and then summed up to obtain the team's total score:

$$
\text{team score} = \sum_{c=1}^{\text{number of categories}} \text{ROTO}_c 
$$

For example, in a 12 team league, the team that is first in home runs will be awarded 12 points for that category, while the last place team in home runs will be awarded 1.  Assuming a 10 category league (standard),  the maximum a team could, therefore, earn is 120 points by placing in first in every category, and oppositedly the minimum would be 10, if a team placed last in every category.

The traditional Standings Gain Points (SGP) model uses this scoring framework and attempts to assign value at the player level for how many places in the standings their production will provide.  It does this by using the specific league's history, and calculating an average stat across previous seasons for each place in the standings, and it does so for every category.  The result then is the average differential across adjacent places in the standings within each category can be calculated, and is then used to calculate the amount needed to earn 1 SGP.  For example, if it is calculated that the average differential amongst all the standing places in Home Runs is 10, then a player projected for 20 Home Runs will earn 2 SGP for that category. Once again, this is repeated for all categories and then all of the results are summed to provide a total SGP for each player.  While this system benefits from its simplicity, and intuitive nature, there are however, some mathematicl flaws and inconsistencies.

The calculation for a player's SGP in a given category can be simply expressed as: $\text{SGP}_c^p = \frac{\text{stat}_c^p}{\delta_c}$ (Note: this applies to counting categories as rate stats are more involved and are discussed later.)  As is easily apparent, is it impossible for a player to contribute negative value with the current method.  That is to say, there is no minimum threshold required before a player starts contributing standings points in a given category.  Upon review of how roto points are calculated, it can be shown that the total amount of ROTO points in a given league across all teams should be:

$$
{\text{League ROTO}} = n_c \sum_{i=1}^{n_{\text{teams}}} i
$$

where $n_c$ is number of categories, and $n_{\text{teams}}$ is the number of teams in the league.  In a league that employs 6 hitting categories, with 12 teams, the total number of ROTO points for hitting alone would then be 432, or 72 per category.  In order to translate this to our SGP scoring system, we would need to remove the baseline being awarded 1 point, which for the same parameters just mentioned would mean 66 per category, and therefore, 396 Hitting SGPs across the rostered universe of players. However, using ATC pre-season projections for the 156 highest valued players (this specific league has 13 hitter slots multiplied by the 12 teams), the pre-season SGP calculations from the traditional model just presented would result in the following:

| R SGP  | RBI SGP | HR SGP | SB SGP | OBP SGP | SLUG SGP | SUM      |
|-------:|--------:|-------:|-------:|--------:|---------:|---------:|
| 737.08 | 722.65  | 461.85 | 148.71 | 2.17    | 21.51    | 2093.96  |

To say this is quite a bit of a delta would be an understatement.  What's even more interesting and actually quite intuitive is the fact that the OBP and SLUG scores are relatively much smaller than their counterparts, and this is due to the traditional calculation being taken against the league historical average; in a theoretical framework, where the projections were anticipating an average run environment compared to recent seasons, and the league rostered the optimal set of players, these rate SGPs would ideally be zero.  At this point, one could observe these values and dismiss the model altogether as mathematically void, and use something such as Z-score sums, etc.  The problem, however, isn't the idea behind this system, its the execution.

In the traditional model, it neglects the fact that in order to actually start earning Standings Gain Points, a player has to exceed a certain threshold determined by the worst place team's value in a given category.  For instance, if all 13 hitters hit 10 home runs each in a given season, the team total would obviously be 130 home runs.  Under the model presented, each of these players would earn $\frac{10}{7.28} = 1.37, \qquad \delta_{\text{HR}} = 7.28$.  Summing this up across all 13 players would result in ~17.8 SGPs for the team in terms of home runs.  This would imply they're projected to be first in the league in home runs! The reality is though, that the average 12th place team has hit 226 home runs in my league historically, a whopping 96 more than what the theoretical team with 17 SGPs is projected to hit.  Here in lies the motivation and foundation for my new and improved model.

In order to properly assess where the team from the 130 home runs example stands, we need to compare it to what the league's baseline is to actually make gains in the standings.  Given that the baseline is 226 in the case of home runs, that means on average the worst place team's average player hit ~17 home runs (the actual number is slightly more than 18, found using a best fit line across the league data points, and removing the extreme values, which will be explained in further detail later).  Therefore, if every hitter on the roster is projected for 17 home runs, this team will be the last place team in the category and will have gained ZERO places in the standings.  Now lets say one player is projected for 25 home runs while the remaining are still projected for that 17 number.  Since the $\delta_{\text{HR}} = 7.28$, this player would receive right above 1 SGP for home runs, and it is intuitive that the team cumulative would now gain them a place in the standings if the 11th place team is only 7 home runs above the last place team.  At last, the team total SGP, which would be the 1+ SGP gained from the player hitting 25 home runs in additional to all the net neutral 17 home run hitters, actually matches their placement in the standings.  

All it took to better align player's contribution to the team's place in the standings is creating a threshold for each category before a player starts accumulating positive value.  What this also achieves is it essentially normalizes the categories for cross comparison amongst one another, as some categories will have much higher thresholds.  For the rate stats, the main difference between this model and the traditional is that rather than compare the player's projection/stat to the league's average, it once again compares the player against the baseline rate, to evaluate how many places in the standings the player's contribution gains the overall team average.  In a later section there is equations and detailed descriptions of variables in order to fully emcompass the methodology.     

---

The following section present a preview of the streamlit app's interface, and how the SGP processed leaderboards, along with projections and up to date stats, are presented to the user.

## Streamlit App
- Latest Version: https://sgp-viewer-110810475909.us-central1.run.app/
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


### OLD Preview / Juxtaposition between This Model and Traditional SGP
This directory contains the fantasy SGP valuation system I created and use directly in my pre-season draft values, and also in-season to inform transactions.   

The crux of this valuation system is that it's based off a popular valuation system called Standing Gain Points, but with a twist: I decided to remove the barrier level stats (the stat level required to actually start gaining SGPs i.e. the average player on the last place team). This is in attempt to get a more accurate representation of how many standing points players are actually contributing above the last place team rather than just the raw SGPs used traditionally by SGP practicioners.  For example, let's say Player X will hit 30 home runs and steal 5 bases, while Player Y is projected for 20 home runs and 15 stolen bases.  The natural question is when deciding on player value is which of these players is more valuable?  Well, if the projection systems are to be trusted we need a way of valuing the weights of different categories. The famous Z-Score calculations will take the mean and standard deviation of each category and apply them to the players projections in order to get a sum of Z-scores for each player across the categories.  This form of normalization and sums are however, only valid for normally distributed statistics.  It has been shown (probably should include that in a notebook for validity) that these categories for the most part do not follow such a distribution, and therefore, the weights applied by the z-score method are not valid.  This brings us to the SGP method, which is already a heavily-utilized method by many fantasy baseball practicioners.  In this system, lets say the user is in a league where each person in the standings on average is separated by 10 home runs, and is seperated on average by 5 stolen bases.  The classical SGP method would calculate this as Player X: 30 hrs / 10 + 5 sbs / 5 = 4 and Player Y: 20 hrs / 10 + 15 sbs / 5 = 5, and therefore, Player Y is more valuable.  What this method forgets to capture is what is the minimum threshold of contributions in each category for a player to start providing SGPs above what is on the wire or even at the bottom of the rostered universe.  That drives the motivation for my system, which assumes a reasonably optimized rostered subset of players (the managers in the league are active enough to roster the best available players), and calculates the thresholds for minimum sufficient contributions as the average player on the 12th place team over the last 4 years (all of the standings for each category have been weighted by recency and averaged in order to calculate league tendencies and to account for differences in run enviornment).  

To further illustrate how this is done, off hand I have calculated that the 12th place team in home runs and stolen bases average a total of 241.3 home runs and 97 stolen bases.  That means, in a league where 13 hitters are rostered, this equates to 18.56 home runs and 7.5 stolen bases per year by the average player on the basement dweller team.  Thus, if a hitter is only contributing 5 stolen bases but hitting 30 home runs, he is positively contributing to your home runs above the last place threshold, but is actually providing negative value and not increasing your sb total above what the last place team is doing a per player rate.  Simply put, this ultimately results in my SGP equation of: ((player_stat__cat_i) - (last_place_team_avg_stat_cat_i/13)) / average_diff_in_standings_cat_i.  For the case mentioned above this means Player X would have a SGP of (30-18.56)/10 + (5-7.5)/5= 1.1433-0.5=.64 and Player Y's result would be (20-18.56)/10 + (15-7.5)/5 = 1.64.  Here, Player Y still wins, but I arbitrarily picked the average standing difference of 10 home runs and 5 stolen bases when in reality the values for my personal league are 7.3 home runs and 12.55 stolen bases which means that hoe runs are almost 2x as valuable as stolen bases past the respective thresholds.  

In fact, for just these two categories for these two specific hypothetical cases using the actual average standing differences and the 12th place team's average player values of 18.56 and 7.5, Player X would have a SGP of 1.369 and for Y it would be .7933, emphasizing the importance of home runs in my league over the years.  Of course, my league isn't just these two categories as we also use R, RBI, OBP, and SLUG, which makes it even more intuitive that these settings would cause home runs to be more valuable than stolen bases.  The sum of all these categories SGPs for each player utilizing various projection systems is the exact ordering I use in my pre-season draft rankings.  As you might suspect, the rate stats (OBP and SLUG) are a little more complex, and require the use of the average player's and team's opportunities across the year in regards to PAs and ABs.  A more in depth look at the calculations can be found in the code.

A fair quesiton at this point is how much added value does this bring over the standard SGP calculations, and the answer is at this point I have not looked into that, and I'm honestly willing to bet it isn't as big of a difference as I'd hope it would be.  However, in theory this is more mathematically sound, even despite some major assumptions and faith in an accurate projection system and consistency in the league's tendencies/run environment which also hold true with the original SGP system itself.

### Original Workbook 
The original (not up to date) valution system workbook itself can be found in the excel macro-enabled workbook titled LeagueStatsSGPInvest.xlsm. Included in this workbook is all of the pre-season and weekly rest of the season updated player valuations along with my league's historical data, and this workbook will continued to be improved upon and soon will become outputs from a python script that will ensure that this is periodically updated and so that the computations can be abstracted out and sped up.  It was created in the off-season prior to the 2024 MLB season and contains multiple in-season updates in order to continously drive actionable decisions for my team.   

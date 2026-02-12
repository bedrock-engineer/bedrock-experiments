# Constructiesafari Rotterdam

| Locatie                                                                                    | Bijzonderheden                                                                                                                                | `.zip`                                                                             |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **NS Station Blaak**                                                                       | Ondergrondse kruising van trein en metro Bovengronds tram, weg en marktplein Luifel met ondersteuning door vakwerkboog Glazen dak metrogebouw | `FME_24247068_1765985199838_179491.zip`                                            |
| Rotta Nova                                                                                 | in aanbouw naast Markthal                                                                                                                     | `FME_24247068_1765985199838_179491.zip`                                            |
| **Markthal**                                                                               | Ondergrondse meerlaagse parkeergarage Boogconstructie gebouw Kabelnetgevel                                                                    | `FME_24247068_1765985199838_179491.zip`                                            |
| Willemsbrug                                                                                | Asymmetrische tuibrug Verankering achtertuien? Overspanning? Fundering?                                                                       |                                                                                  |
| **Koningshavenbrug (“De Hef”)**                                                            | Klassieke vakwerkbrug                                                                                                                         |                                                                                  |
| Maastoren                                                                                  | In-situ betonnen kern met prefabgevel Luifel boven ingang                                                                                     | `FME_24247068_1766343827652_307353.zip`  <br>`FME_24247068_1766386018501_320143.zip` |
| De Rotterdam                                                                               | Multi-use hoogbouwcomplex op meerlaagse parkeerkelder                                                                                         | `FME_24247068_1765987669984_181226.zip`                                            |
| **Erasmusbrug**                                                                            | Asymmetrische tuibrug Fundering Verankering achtertui Overspanning                                                                            | `FME_24247068_1765987669984_181226.zip`                                            |
| **De Zalmhaven**                                                                           | Hoogste woongebouw van Nederland Link naar het vak dynamica (Karel van Dalen) m.b.t. eigenfrequentie en demping                               | `FME_24247068_1765982812802_171436.zip`                                            |
| Wandeling is vanaf hier verder vrij, nu startpunt als eindpunt gekozen, totaal circa 6 km. | Leuvehaven en Wijnhaven-gebied bieden interessante hoogbouw                                                                                   |                                                                                  |

## Removing **/*.zip files from git history

Display all git history in the terminal
```bash
git log --graph --oneline --all
```

Display git history of current branch
```bash
git log --graph --oneline
```

Display git history of all files that comply to a certain glob pattern
```bash
git log --graph --oneline -- "**/*.zip"
```

the `--` after the other --options indicates to the `git log` command that whatever comes after the `--` are no longer --options, but are the arguments.

"We hebben eigenlijk gewoon dit gedaan":

```bash
git rebase -i --exec "<hier een of ander command>" -- <ref (think commit/branch) from which you want to start the rebase>
```

Command & process we actually used to remove Zalmhaven .zip (200+ MB):

```bash
git rebase -i --exec "git rm <file_name> && git commit --amend --no-edit" origin/speckle
```

then, in the terminal editor remove the `exec` lines (which come after the `pick <commit>` lines in the interactive `git rebase -i`) for which the `git rm` command doesn't apply, because the file in the `git rm` command isn't present in those commits.

NOTE: we also completely removed a `pick <commit>` line in which the large .zip was removed from the repo again.

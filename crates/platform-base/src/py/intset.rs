//! A Python `set` of small non-negative ints, in CPython's iteration order.
//!
//! Code that loops over a set of port indices hands them out in the order
//! the hash table holds them -- `hash(i) == i`, linear probing, a perturbed
//! jump, a resize at 60% fill, deleted slots left as dummies -- and that
//! order reaches logs and dicts.  This reproduces `setobject.c` (3.13) for
//! exactly that case.

const MINSIZE: usize = 8;
const LINEAR_PROBES: usize = 9;
const PERTURB_SHIFT: u32 = 5;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Slot {
    Empty,
    Dummy,
    Key(u64),
}

#[derive(Clone, Debug)]
pub struct IntSet {
    table: Vec<Slot>,
    fill: usize,
    used: usize,
}

impl Default for IntSet {
    fn default() -> Self {
        IntSet::new()
    }
}

impl IntSet {
    /// `set()`.
    pub fn new() -> IntSet {
        IntSet {
            table: vec![Slot::Empty; MINSIZE],
            fill: 0,
            used: 0,
        }
    }

    /// `set(iterable)`: added one by one, in the iterable's order.
    pub fn from_iter_ordered(items: impl IntoIterator<Item = u64>) -> IntSet {
        let mut s = IntSet::new();
        for i in items {
            s.add(i);
        }
        s
    }

    fn mask(&self) -> usize {
        self.table.len() - 1
    }

    pub fn len(&self) -> usize {
        self.used
    }

    pub fn is_empty(&self) -> bool {
        self.used == 0
    }

    pub fn contains(&self, key: u64) -> bool {
        self.table.contains(&Slot::Key(key))
    }

    /// `set.add(key)`: `set_add_entry` -- the last dummy on the probe path
    /// is reused once the key is known to be absent.
    pub fn add(&mut self, key: u64) {
        let mask = self.mask();
        let mut i = (key as usize) & mask;
        let mut perturb = key;
        let mut freeslot: Option<usize> = None;
        loop {
            let probes = if i + LINEAR_PROBES <= mask {
                LINEAR_PROBES
            } else {
                0
            };
            for j in 0..=probes {
                match self.table[i + j] {
                    Slot::Empty => {
                        if let Some(f) = freeslot {
                            self.table[f] = Slot::Key(key);
                            self.used += 1;
                            return;
                        }
                        self.table[i + j] = Slot::Key(key);
                        self.fill += 1;
                        self.used += 1;
                        if self.fill * 5 >= mask * 3 {
                            let minused = if self.used > 50000 {
                                self.used * 2
                            } else {
                                self.used * 4
                            };
                            self.resize(minused);
                        }
                        return;
                    }
                    Slot::Key(k) if k == key => return,
                    // The last dummy on the path, not the first.
                    Slot::Dummy => freeslot = Some(i + j),
                    _ => {}
                }
            }
            perturb >>= PERTURB_SHIFT;
            i = (i
                .wrapping_mul(5)
                .wrapping_add(1)
                .wrapping_add(perturb as usize))
                & mask;
        }
    }

    /// `set_table_resize`: the live keys, in table order, into a fresh table.
    fn resize(&mut self, minused: usize) {
        let mut newsize = MINSIZE;
        while newsize <= minused {
            newsize <<= 1;
        }
        // Small and staying small, without dummies to purge: nothing to do.
        if newsize == MINSIZE && self.table.len() == MINSIZE && self.fill == self.used {
            return;
        }
        let old = std::mem::replace(&mut self.table, vec![Slot::Empty; newsize]);
        self.fill = self.used;
        let mask = newsize - 1;
        for slot in old {
            if let Slot::Key(k) = slot {
                insert_clean(&mut self.table, mask, k);
            }
        }
    }

    /// `set.discard(key)`: the slot becomes a dummy.
    pub fn discard(&mut self, key: u64) {
        if let Some(pos) = self.table.iter().position(|s| *s == Slot::Key(key)) {
            self.table[pos] = Slot::Dummy;
            self.used -= 1;
        }
    }

    /// `set.clear()`: back to a small empty table.
    pub fn clear(&mut self) {
        *self = IntSet::new();
    }

    /// `for x in s`.
    pub fn iter(&self) -> impl Iterator<Item = u64> + '_ {
        self.table
            .iter()
            .filter_map(|s| if let Slot::Key(k) = s { Some(*k) } else { None })
    }

    /// `copy.deepcopy(s)`: `set(list(s))`.
    pub fn deepcopy(&self) -> IntSet {
        IntSet::from_iter_ordered(self.iter().collect::<Vec<_>>())
    }
}

/// `set_insert_clean`: a key known not to be there, into a table without
/// dummies.
fn insert_clean(table: &mut [Slot], mask: usize, key: u64) {
    let mut i = (key as usize) & mask;
    let mut perturb = key;
    loop {
        if table[i] == Slot::Empty {
            table[i] = Slot::Key(key);
            return;
        }
        if i + LINEAR_PROBES <= mask {
            for j in 1..=LINEAR_PROBES {
                if table[i + j] == Slot::Empty {
                    table[i + j] = Slot::Key(key);
                    return;
                }
            }
        }
        perturb >>= PERTURB_SHIFT;
        i = (i
            .wrapping_mul(5)
            .wrapping_add(1)
            .wrapping_add(perturb as usize))
            & mask;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Lines of `ops<TAB>python's list(s)`, ops being `a<n>` add, `d<n>`
    /// discard, `c` clear, `k` deepcopy, space-separated: tests/data/
    /// intset.tsv, or the corpus `INTSET_CORPUS` names.
    #[test]
    fn corpus_matches_python() {
        let text = match std::env::var("INTSET_CORPUS") {
            Ok(path) => std::fs::read_to_string(path).unwrap(),
            Err(_) => include_str!("../../tests/data/intset.tsv").to_string(),
        };
        let mut bad = 0;
        for line in text.lines() {
            let (ops, want) = line.split_once('\t').unwrap();
            let mut s = IntSet::new();
            for op in ops.split(' ').filter(|o| !o.is_empty()) {
                let n = op[1..].parse::<u64>().unwrap_or(0);
                match &op[..1] {
                    "a" => s.add(n),
                    "d" => s.discard(n),
                    "c" => s.clear(),
                    "k" => s = s.deepcopy(),
                    _ => panic!(),
                }
            }
            let got = format!(
                "[{}]",
                s.iter()
                    .map(|k| k.to_string())
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            if got != want {
                bad += 1;
                eprintln!("{ops}: python {want} native {got}");
            }
        }
        assert_eq!(bad, 0);
    }
}

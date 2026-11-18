package ua.chynnist.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import io.github.marybezuhla.suvii.TocEntry
import ua.chynnist.R
import ua.chynnist.text.Reading

/**
 * The contents of a document: the larger parts fold open, the part being read is open and its entry marked.
 * A word or a number in the field on top finds entries in the whole document ("24" finds "Стаття 24").
 */
@Composable
fun TocPage(reading: Reading, currentBlock: Int, onPick: (String) -> Unit, onBack: () -> Unit) {
    val scheme = MaterialTheme.colorScheme
    val current = remember(reading, currentBlock) { reading.place(currentBlock)?.entry }
    var query by rememberSaveable { mutableStateOf("") }
    val top = remember(reading) { reading.toc.minOfOrNull { it.level } ?: 0 }
    // The part being read is open from the start
    val currentPart = remember(reading, current) { current?.let { partOf(reading.toc, it, top) } }
    var open by rememberSaveable { mutableStateOf(listOfNotNull(currentPart?.anchor)) }
    val shown = remember(reading, query, open) {
        if (query.isBlank()) visible(reading.toc, top, open.toSet()) else found(reading.toc, query)
    }
    val start = remember(reading) { shown.indexOf(current).coerceAtLeast(0) }
    val list = rememberLazyListState(initialFirstVisibleItemIndex = maxOf(0, start - 2))
    Scaffold(containerColor = scheme.background, topBar = { Bar(stringResource(R.string.toc), onBack) }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.TopCenter) {
            Column(Modifier.widthIn(max = READING_WIDTH).fillMaxWidth()) {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    label = { Text(stringResource(R.string.toc_find)) },
                    placeholder = { Text(stringResource(R.string.toc_find_hint)) },
                    singleLine = true,
                    trailingIcon = {
                        if (query.isNotEmpty()) {
                            IconButton(onClick = { query = "" }) {
                                Icon(painterResource(R.drawable.ic_close), contentDescription = stringResource(R.string.clear))
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                )
                if (shown.isEmpty()) {
                    Text(stringResource(R.string.toc_nothing), style = MaterialTheme.typography.bodyMedium, color = scheme.onSurfaceVariant,
                        modifier = Modifier.padding(16.dp))
                }
                LazyColumn(state = list, contentPadding = PaddingValues(start = 8.dp, end = 8.dp, bottom = 24.dp)) {
                    items(shown) { entry ->
                        val isPart = query.isBlank() && entry.level == top && hasChildren(reading.toc, entry)
                        val isOpen = entry.anchor in open
                        val here = entry == current
                        val openText = stringResource(if (isOpen) R.string.toc_open else R.string.toc_closed)
                        Text(
                            entry.title,
                            style = if (entry.level == top) MaterialTheme.typography.titleSmall else MaterialTheme.typography.bodyMedium,
                            fontWeight = if (entry.level == top || here) FontWeight.SemiBold else FontWeight.Normal,
                            color = if (here) scheme.primary else scheme.onBackground,
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                                .background(if (here) scheme.secondaryContainer else scheme.background, RoundedCornerShape(10.dp))
                                .clickable(role = if (isPart) Role.DropdownList else Role.Button) {
                                    if (isPart) open = if (isOpen) open - entry.anchor else open + entry.anchor else onPick(entry.anchor)
                                }
                                .then(if (isPart) Modifier.semantics { stateDescription = openText } else Modifier)
                                .padding(start = (8 + 16 * (entry.level - top)).dp, end = 8.dp, top = 12.dp, bottom = 12.dp),
                        )
                    }
                }
            }
        }
    }
}

/** The top-level entry [entry] belongs to. */
private fun partOf(toc: List<TocEntry>, entry: TocEntry, top: Int): TocEntry? {
    val at = toc.indexOf(entry)
    return (at downTo 0).asSequence().map { toc[it] }.firstOrNull { it.level == top }
}

private fun hasChildren(toc: List<TocEntry>, entry: TocEntry): Boolean {
    val at = toc.indexOf(entry)
    return at >= 0 && at + 1 < toc.size && toc[at + 1].level > entry.level
}

/** The top-level entries, with everything inside the open ones. */
private fun visible(toc: List<TocEntry>, top: Int, open: Set<String>): List<TocEntry> {
    val out = mutableListOf<TocEntry>()
    var inOpen = true // entries before the first top-level one are always shown
    for (e in toc) {
        if (e.level == top) {
            out += e
            inOpen = e.anchor in open
        } else if (inOpen) {
            out += e
        }
    }
    return out
}

/** Entries whose title has [query]; a number finds "Стаття 24." before the entries that only mention 24. */
private fun found(toc: List<TocEntry>, query: String): List<TocEntry> {
    val q = query.trim().lowercase()
    val number = Regex("^\\d+(-\\d+)?$").matches(q)
    val matches = toc.filter { it.title.lowercase().contains(q) }
    if (!number) return matches
    val named = Regex("^\\S+\\s+${Regex.escape(q)}(\\.|\\s|$)", RegexOption.IGNORE_CASE)
    return matches.filter { named.containsMatchIn(it.title) } + matches.filterNot { named.containsMatchIn(it.title) }
}

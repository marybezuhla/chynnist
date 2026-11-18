package ua.chynnist.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.marybezuhla.suvii.Field
import ua.chynnist.R
import ua.chynnist.data.DocRow
import ua.chynnist.data.Filter
import ua.chynnist.data.Laws
import ua.chynnist.data.Library
import ua.chynnist.data.Order
import ua.chynnist.ui.theme.CardTitle

/** Names of a collection's enum values (kinds, states) in the app's language. */
class Names(private val fields: Map<String, Field>, private val lang: String) {
    fun of(field: String, value: String): String {
        val names = fields[field]?.values?.get(value) ?: return value
        return names[lang] ?: names["uk"] ?: value
    }
}

@Composable
fun rememberNames(fields: Map<String, Field>): Names {
    val lang = LocalConfiguration.current.locales[0].language
    return remember(fields, lang) { Names(fields, if (lang == "en") "en" else "uk") }
}

/** "2026-08-05" as "05.08.2026". */
fun showDate(iso: String): String = iso.split('-').takeIf { it.size == 3 }?.let { (y, m, d) -> "$d.$m.$y" } ?: iso

/**
 * The Documents section: the laws on the phone, narrowed by [filter]. Only numbers are kept for the whole
 * list; the rows are read from the file a page at a time, as they come into sight.
 */
@Composable
fun DocumentsSection(info: Library.Info, filter: Filter, onFilter: (Filter) -> Unit, onOpen: (String) -> Unit, modifier: Modifier = Modifier) {
    val ids by produceState<LongArray?>(null, info, filter) {
        value = null
        value = try {
            Library.read { Laws.ids(it.db, filter) }
        } catch (_: Exception) {
            LongArray(0)
        }
    }
    val pages = remember(ids) { mutableStateMapOf<Int, List<DocRow>>() }
    val list = rememberLazyListState()
    LaunchedEffect(ids) { list.scrollToItem(0) }
    var choosingKinds by rememberSaveable { mutableStateOf(false) }
    val names = rememberNames(info.fields)
    if (choosingKinds) {
        KindsDialog(filter, names, onDone = { choosingKinds = false; if (it != null) onFilter(filter.copy(kinds = it)) })
    }
    val all = ids
    DocumentList(
        total = all?.size,
        row = { i ->
            val page = i / PAGE
            val rows = pages[page]
            if (rows == null && all != null) {
                LaunchedEffect(all, page) {
                    val slice = all.copyOfRange(page * PAGE, minOf(all.size, (page + 1) * PAGE))
                    pages[page] = try {
                        Library.read { Laws.rows(it.db, slice) }
                    } catch (_: Exception) {
                        emptyList()
                    }
                }
            }
            rows?.getOrNull(i - page * PAGE)
        },
        filter = filter,
        names = names,
        onFilter = onFilter,
        onChooseKinds = { choosingKinds = true },
        onOpen = onOpen,
        list = list,
        modifier = modifier,
    )
}

private const val PAGE = 60

/** The list itself, with its filters on top; [row] gives the row at a place, or null while it is read. */
@Composable
fun DocumentList(
    total: Int?,
    row: @Composable (Int) -> DocRow?,
    filter: Filter,
    names: Names,
    onFilter: (Filter) -> Unit,
    onChooseKinds: () -> Unit,
    onOpen: (String) -> Unit,
    list: LazyListState = rememberLazyListState(),
    modifier: Modifier = Modifier,
) {
    val scheme = MaterialTheme.colorScheme
    Box(modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
        LazyColumn(
            Modifier.widthIn(max = READING_WIDTH).fillMaxWidth(),
            state = list,
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item(key = "filters") { Filters(filter, names, onFilter, onChooseKinds) }
            item(key = "count") {
                Text(
                    when (total) {
                        null -> stringResource(R.string.list_reading)
                        else -> pluralStringResource(R.plurals.documents_count, total, total) + " · " +
                            stringResource(if (filter.order == Order.TITLE) R.string.order_title_short else R.string.order_newest_short)
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = scheme.onSurfaceVariant,
                    modifier = Modifier.padding(horizontal = 4.dp),
                )
            }
            if (total == 0) {
                item(key = "none") { NothingFound { onFilter(Filter(activeOnly = false, kinds = emptySet(), order = filter.order)) } }
            }
            if (total != null) {
                items(total, key = { it }) { i -> DocCard(row(i), names, onOpen) }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Filters(filter: Filter, names: Names, onFilter: (Filter) -> Unit, onChooseKinds: () -> Unit) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
        FilterChip(
            selected = filter.activeOnly,
            onClick = { onFilter(filter.copy(activeOnly = !filter.activeOnly)) },
            label = { Text(stringResource(R.string.filter_active)) },
        )
        val kinds = if (filter.kinds.isEmpty()) {
            stringResource(R.string.filter_kinds_all)
        } else {
            filter.kinds.map { names.of("kind", it) }.sorted().joinToString(", ")
        }
        FilterChip(
            selected = filter.kinds.isNotEmpty(),
            onClick = onChooseKinds,
            label = { Text(stringResource(R.string.filter_kinds, kinds), maxLines = 1, overflow = TextOverflow.Ellipsis) },
            modifier = Modifier.widthIn(max = 320.dp),
        )
        FilterChip(
            selected = filter.order == Order.NEWEST,
            onClick = { onFilter(filter.copy(order = if (filter.order == Order.TITLE) Order.NEWEST else Order.TITLE)) },
            label = { Text(stringResource(R.string.order_newest)) },
        )
    }
}

@Composable
private fun DocCard(row: DocRow?, names: Names, onOpen: (String) -> Unit) {
    val scheme = MaterialTheme.colorScheme
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = scheme.surface,
        border = BorderStroke(1.dp, scheme.outlineVariant),
        modifier = Modifier.fillMaxWidth().heightIn(min = 72.dp)
            .then(if (row != null) Modifier.clickable { onOpen(row.path) } else Modifier),
    ) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            // (while a row is read, an empty card of the same kind keeps the list from jumping)
            Text(row?.title.orEmpty(), style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, color = scheme.onSurface)
            if (row != null) {
                val details = listOfNotNull(
                    row.number,
                    row.status?.let { names.of("status", it) },
                    row.edition?.let { stringResource(R.string.edition_of, showDate(it)) },
                ).joinToString(" · ")
                if (details.isNotEmpty()) Text(details, style = MaterialTheme.typography.bodySmall, color = scheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun NothingFound(onShowAll: () -> Unit) {
    Column(
        Modifier.fillMaxWidth().padding(vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(stringResource(R.string.nothing_found), style = CardTitle, textAlign = TextAlign.Center)
        OutlinedButton(onClick = onShowAll) { Text(stringResource(R.string.show_all)) }
    }
}

/** Kinds of documents to show, each with how many there are; [onDone] gets null if nothing was changed. */
@Composable
private fun KindsDialog(filter: Filter, names: Names, onDone: (Set<String>?) -> Unit) {
    val counts by produceState<List<Pair<String, Long>>?>(null, filter.activeOnly) {
        value = try {
            Library.read { Laws.kinds(it.db, filter.activeOnly) }
        } catch (_: Exception) {
            emptyList()
        }
    }
    var chosen by rememberSaveable { mutableStateOf(filter.kinds.toList()) }
    AlertDialog(
        onDismissRequest = { onDone(null) },
        title = { Text(stringResource(R.string.kinds_title), modifier = Modifier.semantics { heading() }) },
        text = {
            val found = counts
            if (found == null) {
                Text(stringResource(R.string.list_reading))
            } else {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    for ((kind, count) in found) {
                        val on = kind in chosen
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 48.dp)
                                .toggleable(on, role = Role.Checkbox) { chosen = if (it) chosen + kind else chosen - kind },
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Checkbox(checked = on, onCheckedChange = null)
                            Text(names.of("kind", kind), style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f).padding(start = 12.dp))
                            Text(count.toString(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        },
        confirmButton = { Button(onClick = { onDone(chosen.toSet()) }) { Text(stringResource(R.string.kinds_apply)) } },
        dismissButton = { TextButton(onClick = { onDone(emptySet()) }) { Text(stringResource(R.string.filter_kinds_all)) } },
    )
}

/** No laws on the phone yet, or a file that could not be opened: what that means, and a way to add them. */
@Composable
fun NoLaws(problem: Library.Problem?, onOpenFile: () -> Unit, modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    Box(modifier.fillMaxSize().verticalScroll(rememberScrollState()), contentAlignment = Alignment.Center) {
        Column(
            Modifier.widthIn(max = READING_WIDTH).fillMaxWidth().padding(32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                stringResource(if (problem == null) R.string.empty_title else R.string.laws_broken),
                style = CardTitle, color = scheme.onBackground, textAlign = TextAlign.Center,
                modifier = Modifier.semantics { heading() },
            )
            Text(
                if (problem == null) stringResource(R.string.empty_documents) else problemText(problem),
                style = MaterialTheme.typography.bodyMedium, color = scheme.onSurfaceVariant, textAlign = TextAlign.Center,
            )
            Button(onClick = onOpenFile, modifier = Modifier.heightIn(min = 48.dp)) { Text(stringResource(R.string.open_file)) }
        }
    }
}

@Composable
fun problemText(problem: Library.Problem): String = stringResource(
    when (problem) {
        Library.Problem.NOT_LAWS -> R.string.problem_not_laws
        Library.Problem.UNTRUSTED -> R.string.problem_untrusted
        Library.Problem.OTHER_COLLECTION -> R.string.problem_other_collection
        Library.Problem.UPDATE_ONLY -> R.string.problem_update_only
        Library.Problem.TOO_BIG -> R.string.problem_too_big
        Library.Problem.NO_SPACE -> R.string.problem_no_space
        Library.Problem.DAMAGED -> R.string.problem_damaged
    },
)

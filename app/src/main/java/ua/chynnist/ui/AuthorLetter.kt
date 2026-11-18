package ua.chynnist.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/*
 * The author's letter (how the app began, the war, the support) with her photo and name, and the
 * official ways to support Ukraine: the same in all of the author's apps. Links only open in the
 * browser; the app learns nothing of it.
 */

/** One organisation: its name, what it does, and its official site (no tracking marks in the link). */
private class Cause(val name: Int, val what: Int, val url: Int)

// Only official, public channels: no single foundation or person is singled out
private val DEFENCE = listOf(
    Cause(ua.chynnist.R.string.about_org_united24, ua.chynnist.R.string.about_org_united24_defence, ua.chynnist.R.string.about_org_united24_url),
    Cause(ua.chynnist.R.string.about_org_nbu, ua.chynnist.R.string.about_org_nbu_what, ua.chynnist.R.string.about_org_nbu_url),
    // Not a fundraiser: the state's defence-tech cluster, to learn about it
    Cause(ua.chynnist.R.string.about_org_brave1, ua.chynnist.R.string.about_org_brave1_what, ua.chynnist.R.string.about_org_brave1_url),
)

private val HUMANITARIAN = listOf(
    Cause(ua.chynnist.R.string.about_org_united24, ua.chynnist.R.string.about_org_united24_humanitarian, ua.chynnist.R.string.about_org_united24_url),
    Cause(ua.chynnist.R.string.about_org_redcross, ua.chynnist.R.string.about_org_redcross_what, ua.chynnist.R.string.about_org_redcross_url),
)

private val LETTER = listOf(ua.chynnist.R.string.about_letter_1, ua.chynnist.R.string.about_letter_2, ua.chynnist.R.string.about_letter_3, ua.chynnist.R.string.about_letter_4, ua.chynnist.R.string.about_letter_5, ua.chynnist.R.string.about_letter_6, ua.chynnist.R.string.about_letter_7)

/** The letter in a card: every paragraph in the middle, the signature, the photo and the name. */
@Composable
fun AuthorLetter(modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = scheme.surface),
        border = BorderStroke(1.dp, scheme.outlineVariant),
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            for (p in LETTER) {
                Text(stringResource(p), style = MaterialTheme.typography.bodyLarge, color = scheme.onSurface,
                    textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
            }
            Text(stringResource(ua.chynnist.R.string.about_letter_signature), style = MaterialTheme.typography.bodyLarge,
                color = scheme.primary, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
            Image(
                painterResource(ua.chynnist.R.drawable.author_photo),
                // The name below says who it is
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.align(Alignment.CenterHorizontally).padding(top = 4.dp).size(72.dp)
                    .clip(CircleShape).border(1.dp, scheme.outlineVariant, CircleShape),
            )
            Text(stringResource(ua.chynnist.R.string.about_author_name), style = MaterialTheme.typography.bodyMedium, color = scheme.onSurface,
                textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
        }
    }
}

/** Support Ukraine: defence and humanitarian aid, official sites only; [open] opens a link in the browser. */
@Composable
fun SupportUkraine(open: (String) -> Unit, modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    Column(modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(stringResource(ua.chynnist.R.string.about_support_title), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold,
            color = scheme.onSurface, textAlign = TextAlign.Center, modifier = Modifier.semantics { heading() })
        Spacer(Modifier.height(4.dp))
        Text(stringResource(ua.chynnist.R.string.about_support_note), style = MaterialTheme.typography.bodyMedium, color = scheme.onSurfaceVariant,
            textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(16.dp))
        CauseGroup(ua.chynnist.R.string.about_support_defence, DEFENCE, open)
        Spacer(Modifier.height(16.dp))
        CauseGroup(ua.chynnist.R.string.about_support_humanitarian, HUMANITARIAN, open)
        Spacer(Modifier.height(12.dp))
        Text(stringResource(ua.chynnist.R.string.about_support_any), style = MaterialTheme.typography.bodyMedium, color = scheme.onSurfaceVariant,
            textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun CauseGroup(title: Int, causes: List<Cause>, open: (String) -> Unit) {
    val scheme = MaterialTheme.colorScheme
    Text(stringResource(title), style = MaterialTheme.typography.titleMedium, color = scheme.primary,
        fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center, modifier = Modifier.semantics { heading() })
    Spacer(Modifier.height(8.dp))
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = scheme.surface),
        border = BorderStroke(1.dp, scheme.outlineVariant),
        modifier = Modifier.fillMaxWidth(),
    ) {
        for ((i, cause) in causes.withIndex()) {
            if (i > 0) Box(Modifier.fillMaxWidth().padding(horizontal = 16.dp).height(1.dp).background(scheme.outlineVariant))
            val url = stringResource(cause.url)
            Column(
                Modifier.fillMaxWidth().heightIn(min = 64.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .clickable(role = Role.Button, onClickLabel = stringResource(ua.chynnist.R.string.about_open_site)) { open(url) }
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(stringResource(cause.name) + " ↗", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold,
                    color = scheme.onSurface, textAlign = TextAlign.Center)
                Text(stringResource(cause.what), style = MaterialTheme.typography.bodyMedium, color = scheme.onSurfaceVariant,
                    textAlign = TextAlign.Center)
                // Only the site's name: where it leads, readable at a glance
                Text(url.removePrefix("https://").substringBefore('/'), style = MaterialTheme.typography.labelMedium, color = scheme.primary)
            }
        }
    }
}

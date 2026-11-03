export function Footer({ siteName, built, extra }: { siteName: string; built: string; extra?: string }) {
  return (
    <footer>
      <p>
        Built {built} from data collected through the Riot Games API.{extra ? ` ${extra}` : ""}
      </p>
      {/* Riot's required legal notice, with the product name filled in */}
      <p>
        {siteName} isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone
        officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties
        are trademarks or registered trademarks of Riot Games, Inc.
      </p>
    </footer>
  );
}

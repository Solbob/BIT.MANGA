import Head from "next/head";

import "@/styles/globals.css";

export default function App({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>BIT.MANGA — Stories, frame by frame</title>
        <meta name="description" content="Find your next favorite manga. Read free stories or unlock every chapter with Premium." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <Component {...pageProps} />
    </>
  );
}

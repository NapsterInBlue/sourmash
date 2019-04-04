use std::path::{Path, PathBuf};
use std::rc::Rc;

use bio::io::fasta;
use failure::Error;
use log::info;
use ocf::{get_input, get_output, CompressionFormat};

use crate::index::storage::{FSStorage, Storage};
use crate::index::{Comparable, Dataset, Index, UKHSTree};
use crate::signatures::ukhs::{FlatUKHS, UKHSTrait, UniqueUKHS};
use crate::signatures::{Signature, SigsTrait};

pub fn draff_index(sig_files: Vec<&str>, outfile: &str) -> Result<(), Error> {
    let storage: Rc<dyn Storage> = Rc::new(
        FSStorage::new(".".into(), ".draff".into()), // TODO: use outfile
    );

    let mut index = UKHSTree::builder()
        .storage(Rc::clone(&storage))
        .build()
        .unwrap();

    for filename in sig_files {
        // TODO: check for stdin? can also use get_input()?

        let sig = FlatUKHS::load(&filename)?;

        let mut dataset: Dataset<Signature> = sig.into();
        // TODO: properly set name, filename, storage for the dataset
        dataset.filename = String::from(Path::new(filename).file_name().unwrap().to_str().unwrap());
        dataset.storage = Some(Rc::clone(&storage));

        index.insert(&dataset)?;
    }

    // TODO: implement to_writer and use this?
    //let mut output = get_output(outfile, CompressionFormat::No)?;
    //index.to_writer(&mut output)?

    index.save_file(outfile, None)
}

pub fn draff_compare(sigs: Vec<&str>) -> Result<(), Error> {
    let mut dists = vec![vec![0.; sigs.len()]; sigs.len()];
    let loaded_sigs: Vec<FlatUKHS> = sigs.iter().map(|s| FlatUKHS::load(s).unwrap()).collect();

    for (i, sig1) in loaded_sigs.iter().enumerate() {
        for (j, sig2) in loaded_sigs.iter().enumerate() {
            dists[i][j] = 1. - sig1.distance(sig2);
        }
    }

    for row in dists {
        println!("{:.2?}", row);
    }

    Ok(())
}

pub fn draff_search(index: &str, query: &str) -> Result<(), Error> {
    let index = UKHSTree::from_path(index)?;

    let sig = FlatUKHS::load(query)?;
    let dataset: Dataset<Signature> = sig.into();

    for found in index.search(&dataset, 0.2, false)? {
        println!("{:.2}: {:?}", dataset.similarity(found), found);
    }

    Ok(())
}

pub fn draff_signature(files: Vec<&str>, k: usize, w: usize) -> Result<(), Error> {
    for filename in files {
        // TODO: check for stdin?

        let mut ukhs = UniqueUKHS::new(k, w)?;

        info!("Build signature for {} with W={}, K={}...", filename, w, k);

        let (input, _) = get_input(filename)?;
        let reader = fasta::Reader::new(input);

        for record in reader.records() {
            // TODO: N in sequence?
            ukhs.add_sequence(record?.seq(), false)?;
        }

        let mut outfile = PathBuf::from(filename);
        outfile.set_extension("sig");

        let mut output = get_output(outfile.to_str().unwrap(), CompressionFormat::No)?;

        let flat: FlatUKHS = ukhs.into();
        flat.to_writer(&mut output)?
    }
    info!("Done.");

    Ok(())
}

use std::ffi::CStr;
use std::io;
use std::mem;
use std::os::raw::c_char;
use std::slice;

use ocf::get_input;
use serde_json;

use crate::utils::SourmashStr;
use crate::{KmerMinHash, Signature};

// Signature methods

#[no_mangle]
pub unsafe extern "C" fn signature_new() -> *mut Signature {
    mem::transmute(Box::new(Signature::default()))
}

#[no_mangle]
pub extern "C" fn signature_free(ptr: *mut Signature) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        Box::from_raw(ptr);
    }
}

ffi_fn! {
unsafe fn signature_set_name(ptr: *mut Signature, name: *const c_char) ->
    Result<()> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };
    let c_str = {
        assert!(!name.is_null());

        CStr::from_ptr(name)
    };

    if let Ok(name) = c_str.to_str() {
        sig.name = Some(name.to_string())
    }
    Ok(())
}
}

ffi_fn! {
unsafe fn signature_set_filename(ptr: *mut Signature, name: *const c_char) ->
    Result<()> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };
    let c_str = {
        assert!(!name.is_null());

        CStr::from_ptr(name)
    };

    if let Ok(name) = c_str.to_str() {
        sig.filename = Some(name.to_string())
    }
    Ok(())
}
}

ffi_fn! {
unsafe fn signature_push_mh(ptr: *mut Signature, other: *const KmerMinHash) ->
    Result<()> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };
    let mh = {
       assert!(!other.is_null());
       &*other
    };

    sig.signatures.push(mh.clone());
    Ok(())
}
}

ffi_fn! {
unsafe fn signature_set_mh(ptr: *mut Signature, other: *const KmerMinHash) ->
    Result<()> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };
    let mh = {
       assert!(!other.is_null());
       &*other
    };

    sig.signatures = vec![mh.clone()];
    Ok(())
}
}

ffi_fn! {
unsafe fn signature_get_name(ptr: *mut Signature) -> Result<SourmashStr> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };

    if let Some(ref name) = sig.name {
        Ok(SourmashStr::from_string(name.to_string()))
    } else {
        Ok(SourmashStr::from_string("".to_string()))
    }
}
}

ffi_fn! {
unsafe fn signature_get_filename(ptr: *mut Signature) -> Result<SourmashStr> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };

    if let Some(ref name) = sig.filename {
        Ok(SourmashStr::from_string(name.to_string()))
    } else {
        Ok(SourmashStr::from_string("".to_string()))
    }
}
}

ffi_fn! {
unsafe fn signature_get_license(ptr: *mut Signature) -> Result<SourmashStr> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };

    Ok(SourmashStr::from_string(sig.license.to_string()))
}
}

ffi_fn! {
unsafe fn signature_first_mh(ptr: *mut Signature) -> Result<*mut KmerMinHash> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };

    if let Some(mh) = sig.signatures.get(0) {
        Ok(mem::transmute(Box::new(mh.clone())))
    } else {
        // TODO: this is totally wrong
        Ok(mem::transmute(Box::new(KmerMinHash::default())))
    }
}
}

ffi_fn! {
unsafe fn signature_eq(ptr: *mut Signature, other: *mut Signature) -> Result<bool> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };

    let other_sig = {
        assert!(!other.is_null());
        &mut *other
    };

    Ok(sig == other_sig)
}
}

ffi_fn! {
unsafe fn signature_save_json(ptr: *mut Signature) -> Result<SourmashStr> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };

    let st = serde_json::to_string(sig)?;
    Ok(SourmashStr::from_string(st))
}
}

ffi_fn! {
unsafe fn signature_get_mhs(ptr: *mut Signature, size: *mut usize) -> Result<*mut *mut KmerMinHash> {
    let sig = {
        assert!(!ptr.is_null());
        &mut *ptr
    };

    let output = sig.signatures.clone();

    let ptr_sigs: Vec<*mut Signature> = output.into_iter().map(|x| {
      Box::into_raw(Box::new(x)) as *mut Signature
    }).collect();

    let b = ptr_sigs.into_boxed_slice();
    *size = b.len();

    Ok(Box::into_raw(b) as *mut *mut KmerMinHash)
}
}

ffi_fn! {
unsafe fn signatures_save_buffer(ptr: *mut *mut Signature, size: usize) -> Result<SourmashStr> {
    let sigs = {
        assert!(!ptr.is_null());
        slice::from_raw_parts(ptr, size)
    };

    let rsigs: Vec<&Signature> = sigs.iter().map(|x| x.as_ref().unwrap()).collect();
    let st = serde_json::to_string(&rsigs)?;
    Ok(SourmashStr::from_string(st))
}
}

ffi_fn! {
unsafe fn signatures_load_path(ptr: *const c_char,
                               ignore_md5sum: bool,
                               ksize: usize,
                               select_moltype: *const c_char,
                               size: *mut usize) -> Result<*mut *mut Signature> {
    let buf = {
        assert!(!ptr.is_null());
        CStr::from_ptr(ptr)
    };

    let moltype = {
        if select_moltype.is_null() {
          None
        } else {
          Some(CStr::from_ptr(select_moltype).to_str()?)
        }
    };

    // TODO: implement ignore_md5sum

    let (mut input, _) = get_input(buf.to_str()?)?;
    let filtered_sigs = Signature::load_signatures(&mut input, ksize, moltype, None)?;

    let ptr_sigs: Vec<*mut Signature> = filtered_sigs.into_iter().map(|x| {
      Box::into_raw(Box::new(x)) as *mut Signature
    }).collect();

    let b = ptr_sigs.into_boxed_slice();
    *size = b.len();

    Ok(Box::into_raw(b) as *mut *mut Signature)
}
}
ffi_fn! {
unsafe fn signatures_load_buffer(ptr: *const c_char,
                                 insize: usize,
                                 ignore_md5sum: bool,
                                 ksize: usize,
                                 select_moltype: *const c_char,
                                 size: *mut usize) -> Result<*mut *mut Signature> {
    let buf = {
        assert!(!ptr.is_null());
        slice::from_raw_parts(ptr as *mut u8, insize)
    };

    let moltype = {
        if select_moltype.is_null() {
          None
        } else {
          Some(CStr::from_ptr(select_moltype).to_str()?)
        }
    };

    // TODO: implement ignore_md5sum

    let mut reader = io::BufReader::new(buf);
    let filtered_sigs = Signature::load_signatures(&mut reader, ksize, moltype, None)?;

    let ptr_sigs: Vec<*mut Signature> = filtered_sigs.into_iter().map(|x| {
      Box::into_raw(Box::new(x)) as *mut Signature
    }).collect();

    let b = ptr_sigs.into_boxed_slice();
    *size = b.len();

    Ok(Box::into_raw(b) as *mut *mut Signature)
}
}